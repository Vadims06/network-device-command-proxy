"""Shared transport and response validation for vendor adapters."""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from typing import Any, Callable

from pydantic import BaseModel, ValidationError
from scrapli.exceptions import ScrapliAuthenticationFailed, ScrapliException

from device_command_proxy.contracts import ErrorCode, ExecutionError
from device_command_proxy.operation_types import Operation
from device_command_proxy.operations import operation_spec


_logger = logging.getLogger(__name__)

DriverFactory = Callable[[], Any]
MAX_OUTPUT_BYTES = 1_000_000


class OutputFormat(StrEnum):
    JSON = "json"
    TEXT = "text"


class DeviceAdapter:
    """Run allow-listed operations and validate their public result models."""

    def __init__(self, driver_factory: DriverFactory):
        self._driver_factory = driver_factory
        self._operation_handlers: dict[Operation, Callable[..., BaseModel]] = {}

    def run(self, operation: str, **arguments: Any) -> dict[str, Any]:
        try:
            operation_key = Operation(operation)
        except ValueError as exception:
            raise ExecutionError(
                ErrorCode.UNSUPPORTED_OPERATION,
                "operation is not supported by platform",
            ) from exception

        operation_handler = self._operation_handlers.get(operation_key)
        if operation_handler is None:
            raise ExecutionError(
                ErrorCode.UNSUPPORTED_OPERATION,
                "operation is not supported by platform",
            )

        try:
            result = operation_handler(**arguments)
            validated_result = operation_spec(operation_key).response_model.model_validate(
                result
            )
            return validated_result.model_dump(mode="json")
        except ExecutionError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError) as exception:
            _logger.warning(
                "invalid device response during %r: %s",
                operation_key.value,
                type(exception).__name__,
            )
            raise ExecutionError(
                ErrorCode.PARSE_ERROR,
                "device returned an invalid response",
            ) from exception

    def _send_command(
        self,
        command: str,
        *,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> Any:
        try:
            with self._driver_factory() as driver:
                response = driver.send_command(command)
        except ScrapliAuthenticationFailed as exception:
            _logger.warning("device authentication failed: %s", exception)
            raise ExecutionError(
                ErrorCode.AUTHENTICATION_FAILED, "device rejected the credentials"
            ) from exception
        except (ScrapliException, OSError) as exception:
            _logger.warning(
                "device connection failed: %s: %s",
                type(exception).__name__,
                exception,
            )
            raise ExecutionError(
                ErrorCode.DEVICE_UNREACHABLE, "device connection failed"
            ) from exception

        if response.failed:
            raise ExecutionError(ErrorCode.COMMAND_FAILED, "device command failed")
        if len(response.result) > MAX_OUTPUT_BYTES:
            raise ExecutionError(
                ErrorCode.OUTPUT_TOO_LARGE,
                "device output exceeds the size limit",
            )
        if output_format is OutputFormat.TEXT:
            return response.result
        return json.loads(response.result)
