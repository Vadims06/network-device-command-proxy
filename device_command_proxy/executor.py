"""Globally bounded batch execution with structured partial failures."""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor, wait
from threading import Lock, Semaphore
from time import perf_counter
from typing import Any, Callable, Mapping

from device_command_proxy import audit
from device_command_proxy.contracts import (
    CredentialProvider,
    DeviceResult,
    ErrorCode,
    ExecutionError,
    InventoryProvider,
    OperationError,
    OperationRequest,
)
from device_command_proxy.validation import (
    validate_arguments,
    validate_devices,
    validate_operation,
)


_logger = logging.getLogger(__name__)

AdapterFactory = Callable[[Any, Any], Any]


class BatchExecutor:
    def __init__(
        self,
        inventory: InventoryProvider,
        credentials: CredentialProvider,
        adapter_factories: Mapping[str, AdapterFactory],
        unsupported_fields: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
        *,
        max_workers: int = 20,
        queue_capacity: int = 100,
        request_deadline_sec: float = 30.0,
    ):
        if not 1 <= max_workers <= 20:
            raise ValueError("max_workers must be between 1 and 20")
        if not 0 <= queue_capacity <= 100:
            raise ValueError("queue_capacity must be between 0 and 100")
        if not 0 < request_deadline_sec <= 30:
            raise ValueError("request_deadline_sec must be between 0 and 30")
        self._inventory = inventory
        self._credentials = credentials
        self._adapter_factories = dict(adapter_factories)
        self._unsupported_fields = dict(unsupported_fields or {})
        self._request_deadline_sec = request_deadline_sec
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._capacity = Semaphore(max_workers + queue_capacity)
        self._device_locks: dict[str, Lock] = {}
        self._device_locks_guard = Lock()

    def execute(self, request: OperationRequest) -> tuple[DeviceResult, ...]:
        validate_operation(request.operation)
        validate_devices(request.devices)
        results: dict[str, DeviceResult] = {}
        futures: dict[Future, str] = {}
        # Written by each worker as soon as it resolves its device, so a task
        # still running at the deadline is still reported against its real
        # platform instead of "unknown".
        resolved_platforms: dict[str, str] = {}
        validated_arguments_by_device: dict[str, Mapping[str, Any]] = {}
        for device_name in request.devices:
            if not self._capacity.acquire(blocking=False):
                results[device_name] = self._error_result(
                    device_name,
                    request.operation,
                    "unknown",
                    ErrorCode.QUEUE_FULL,
                    "execution queue is full",
                )
                continue
            future = self._thread_pool.submit(
                self._execute_device,
                device_name,
                request.operation,
                request.arguments,
                resolved_platforms,
                validated_arguments_by_device,
            )
            future.add_done_callback(lambda _future: self._capacity.release())
            futures[future] = device_name

        completed, incomplete = wait(
            futures,
            timeout=self._request_deadline_sec,
        )
        for future in completed:
            results[futures[future]] = future.result()
        for future in incomplete:
            future.cancel()
            device_name = futures[future]
            platform = resolved_platforms.get(device_name, "unknown")
            results[device_name] = self._error_result(
                device_name,
                request.operation,
                platform,
                ErrorCode.DEADLINE_EXCEEDED,
                "request deadline exceeded",
                unsupported_fields=self._platform_unsupported_fields(
                    platform, request.operation
                ),
            )
        for device_name in request.devices:
            audit.record(
                results[device_name],
                request_id=request.request_id,
                arguments=validated_arguments_by_device.get(device_name, {}),
            )
        return tuple(results[device_name] for device_name in request.devices)

    def close(self, *, wait: bool = True) -> None:
        self._thread_pool.shutdown(wait=wait, cancel_futures=True)

    def _execute_device(
        self,
        device_name: str,
        operation: str,
        arguments: Mapping[str, Any],
        resolved_platforms: dict[str, str],
        validated_arguments_by_device: dict[str, Mapping[str, Any]],
    ) -> DeviceResult:
        started_at = perf_counter()
        platform = "unknown"
        try:
            device = self._inventory.get_device(device_name)
            platform = device.platform
            resolved_platforms[device_name] = platform
            device_arguments = validate_arguments(operation, arguments, device)
            validated_arguments_by_device[device_name] = device_arguments
            adapter_factory = self._adapter_factories.get(platform)
            if adapter_factory is None:
                raise ExecutionError(
                    ErrorCode.UNSUPPORTED_PLATFORM,
                    "device platform is not supported",
                )
            credentials = self._credentials.get_credentials(
                device.credential_profile
            )
            with self._device_lock(device_name):
                data = adapter_factory(device, credentials).run(
                    operation,
                    **device_arguments,
                )
            return DeviceResult(
                device=device_name,
                operation=operation,
                platform=platform,
                status="success",
                data=data,
                duration_ms=int((perf_counter() - started_at) * 1000),
                unsupported_fields=self._platform_unsupported_fields(
                    platform, operation
                ),
            )
        except ExecutionError as exception:
            return self._error_result(
                device_name,
                operation,
                platform,
                exception.code,
                str(exception),
                started_at=started_at,
                unsupported_fields=self._platform_unsupported_fields(
                    platform, operation
                ),
            )
        except Exception:
            # internal_error carries no detail to the caller on purpose, so
            # the traceback has to be recorded here or it is lost entirely.
            _logger.exception(
                "internal execution error on device %s during %s",
                device_name,
                operation,
            )
            return self._error_result(
                device_name,
                operation,
                platform,
                ErrorCode.INTERNAL_ERROR,
                "internal execution error",
                started_at=started_at,
                unsupported_fields=self._platform_unsupported_fields(
                    platform, operation
                ),
            )

    def _platform_unsupported_fields(
        self, platform: str, operation: str
    ) -> tuple[str, ...]:
        return self._unsupported_fields.get(platform, {}).get(operation, ())

    def _device_lock(self, device_name: str) -> Lock:
        with self._device_locks_guard:
            return self._device_locks.setdefault(device_name, Lock())

    @staticmethod
    def _error_result(
        device_name: str,
        operation: str,
        platform: str,
        code: ErrorCode,
        message: str,
        *,
        started_at: float | None = None,
        unsupported_fields: tuple[str, ...] = (),
    ) -> DeviceResult:
        duration_ms = 0
        if started_at is not None:
            duration_ms = int((perf_counter() - started_at) * 1000)
        return DeviceResult(
            device=device_name,
            operation=operation,
            platform=platform,
            status="error",
            data=None,
            duration_ms=duration_ms,
            error=OperationError(code=code, message=message),
            unsupported_fields=unsupported_fields,
        )
