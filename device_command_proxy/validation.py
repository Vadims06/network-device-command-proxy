"""Validation at the semantic operation boundary."""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Mapping

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError
from device_command_proxy.operations import (
    ALLOWED_OPERATIONS,
    ArgumentKind,
    operation_spec,
)


MAX_DEVICES = 20
# Slash and colon are part of ordinary interface names on several platforms
# (ge-0/0/0.0, xe-0/0/0:1). The pattern is the safety boundary before the
# validated name reaches the fixed vendor command.
INTERFACE_PATTERN = re.compile(r"^[a-zA-Z0-9_.:/-]+$")
# The only argument keys any operation ever accepts. Shared with audit.py so
# a caller cannot get an arbitrary key logged verbatim by attaching it to a
# request: validate_arguments() rejects it, but the raw request arguments
# still reach the audit record regardless of whether validation succeeded.
LOGGABLE_ARGUMENT_KEYS = frozenset({"interface", "prefix"})


def is_valid_interface_name(interface_name: Any) -> bool:
    """Shared by the request path and inventory loading, so the two agree."""
    return isinstance(interface_name, str) and bool(
        INTERFACE_PATTERN.fullmatch(interface_name)
    )


def is_valid_prefix(value: Any) -> bool:
    """Shared by request validation and audit-log redaction.

    Without this, an unvalidated string placed in the "prefix" argument key
    (which the request path would reject) still reaches the audit log
    verbatim, since key-name filtering alone says nothing about the value.
    """
    if not isinstance(value, str):
        return False
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        return False
    return True


def validate_operation(operation: str) -> None:
    """Reject an operation that does not exist, before any device is touched.

    Whether an operation exists at all does not depend on the device, so it is
    a request-level error like the device list. A per-device
    ``unsupported_operation`` still means what it should: the operation exists
    but this platform's driver does not implement it.
    """
    if operation not in ALLOWED_OPERATIONS:
        raise ExecutionError(
            ErrorCode.UNSUPPORTED_OPERATION,
            "operation is not allowed",
        )


def validate_devices(devices: tuple[str, ...]) -> None:
    if not devices or len(devices) > MAX_DEVICES:
        raise ExecutionError(
            ErrorCode.INVALID_REQUEST,
            "devices must contain between 1 and 20 names",
        )
    if len(set(devices)) != len(devices):
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "device names must be unique")
    if any(not device or len(device) > 64 for device in devices):
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "invalid device name")


def validate_arguments(
    operation: str,
    arguments: Mapping[str, Any],
    device: DeviceProfile,
) -> dict[str, Any]:
    if operation not in ALLOWED_OPERATIONS:
        raise ExecutionError(
            ErrorCode.UNSUPPORTED_OPERATION,
            "operation is not allowed",
        )
    specification = operation_spec(operation)
    if specification.argument_kind is ArgumentKind.NONE:
        if arguments:
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "operation takes no arguments")
        return {}
    if specification.argument_kind is ArgumentKind.INTERFACE:
        if set(arguments) != {"interface"}:
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "interface is required")
        interface_name = arguments["interface"]
        if not is_valid_interface_name(interface_name):
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "invalid interface")
        return {"interface": interface_name}

    if specification.argument_kind is not ArgumentKind.PREFIX:
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "unsupported argument kind")
    if set(arguments) != {"prefix"} or not isinstance(arguments["prefix"], str):
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "prefix is required")
    try:
        prefix = str(ipaddress.ip_network(arguments["prefix"], strict=False))
    except ValueError as exception:
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "invalid prefix") from exception
    return {"prefix": prefix}
