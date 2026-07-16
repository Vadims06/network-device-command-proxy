"""Validation at the semantic operation boundary."""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Mapping

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError


MAX_DEVICES = 20
INTERFACE_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
NO_ARGUMENT_OPERATIONS = frozenset(
    {
        "get_ospf_neighbors",
        "get_ospf_neighbor_detail",
        "get_ospf_status",
    }
)
INTERFACE_OPERATIONS = frozenset(
    {"get_interface_status", "get_ospf_interface"}
)
PREFIX_OPERATIONS = frozenset({"get_route"})
ALLOWED_OPERATIONS = (
    NO_ARGUMENT_OPERATIONS | INTERFACE_OPERATIONS | PREFIX_OPERATIONS
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
    if operation in NO_ARGUMENT_OPERATIONS:
        if arguments:
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "operation takes no arguments")
        return {}
    if operation in INTERFACE_OPERATIONS:
        if set(arguments) != {"interface"}:
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "interface is required")
        interface_name = arguments["interface"]
        if not isinstance(interface_name, str) or not INTERFACE_PATTERN.fullmatch(
            interface_name
        ):
            raise ExecutionError(ErrorCode.INVALID_REQUEST, "invalid interface")
        if interface_name not in device.interfaces:
            raise ExecutionError(
                ErrorCode.INVALID_REQUEST,
                "interface is not present on device",
            )
        return {"interface": interface_name}

    if set(arguments) != {"prefix"} or not isinstance(arguments["prefix"], str):
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "prefix is required")
    try:
        prefix = str(ipaddress.ip_network(arguments["prefix"], strict=False))
    except ValueError as exception:
        raise ExecutionError(ErrorCode.INVALID_REQUEST, "invalid prefix") from exception
    return {"prefix": prefix}
