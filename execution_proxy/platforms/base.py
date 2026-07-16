"""Shared adapter machinery reused by every per-vendor driver."""

from __future__ import annotations

import json
from typing import Any, Callable

from scrapli.exceptions import ScrapliException

from execution_proxy.contracts import ErrorCode, ExecutionError


DriverFactory = Callable[[], Any]

MAX_OUTPUT_BYTES = 1_000_000


class DeviceAdapter:
    """Runs a semantic operation over a Scrapli driver and normalizes output.

    Subclasses only need to populate ``self._operation_handlers`` (mapping
    operation name to a method returning ``(command, normalizer)``).
    """

    def __init__(self, driver_factory: DriverFactory):
        self._driver_factory = driver_factory
        self._operation_handlers: dict[str, Callable[..., Any]] = {}

    def run(self, operation: str, **arguments: Any) -> dict[str, Any]:
        operation_handler = self._operation_handlers.get(operation)
        if operation_handler is None:
            raise ExecutionError(
                ErrorCode.UNSUPPORTED_OPERATION,
                "operation is not supported by platform",
            )
        command, normalizer = operation_handler(**arguments)
        try:
            with self._driver_factory() as driver:
                response = driver.send_command(command)
        except (ScrapliException, OSError) as exception:
            raise ExecutionError(
                ErrorCode.DEVICE_UNREACHABLE, "device connection failed"
            ) from exception
        if response.failed:
            raise ExecutionError(ErrorCode.DEVICE_UNREACHABLE, "device command failed")
        if len(response.result) > MAX_OUTPUT_BYTES:
            raise ExecutionError(
                ErrorCode.OUTPUT_TOO_LARGE,
                "device output exceeds the size limit",
            )
        try:
            payload = json.loads(response.result)
            return normalizer(payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exception:
            raise ExecutionError(
                ErrorCode.INTERNAL_ERROR,
                "device returned an invalid response",
            ) from exception
