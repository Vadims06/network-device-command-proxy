"""Stable contracts shared by inventory, credentials, adapters, and HTTP."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Protocol

from device_command_proxy.operation_types import AuthenticationType, ResultStatus


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    DEVICE_NOT_FOUND = "device_not_found"
    INVENTORY_UNAVAILABLE = "inventory_unavailable"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    DEVICE_UNREACHABLE = "device_unreachable"
    AUTHENTICATION_FAILED = "authentication_failed"
    COMMAND_FAILED = "command_failed"
    PARSE_ERROR = "parse_error"
    OUTPUT_TOO_LARGE = "output_too_large"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    QUEUE_FULL = "queue_full"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class DeviceProfile:
    name: str
    host: str
    port: int
    platform: str
    credential_profile: str
    interfaces: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, repr=False)
class DeviceCredentials:
    username: str
    authentication_type: AuthenticationType
    password: str | None = None
    private_key: str | None = None
    private_key_passphrase: str | None = None
    ssh_certificate: str | None = None

    def __post_init__(self) -> None:
        try:
            authentication_type = AuthenticationType(self.authentication_type)
        except ValueError as exception:
            raise ValueError(
                "authentication_type must be password or private_key"
            ) from exception
        object.__setattr__(self, "authentication_type", authentication_type)
        if authentication_type is AuthenticationType.PASSWORD and not self.password:
            raise ValueError("password credentials require password")
        if authentication_type is AuthenticationType.PRIVATE_KEY and not self.private_key:
            raise ValueError("private_key credentials require private_key")


class CredentialProvider(Protocol):
    def get_credentials(self, credential_profile: str) -> DeviceCredentials:
        """Return credentials for one fixed logical profile."""


class InventoryProvider(Protocol):
    def get_device(self, device_name: str) -> DeviceProfile:
        """Resolve a device through the live inventory."""


@dataclass(frozen=True)
class OperationRequest:
    operation: str
    devices: tuple[str, ...]
    arguments: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = ""


@dataclass(frozen=True)
class OperationError:
    code: ErrorCode
    message: str


@dataclass(frozen=True)
class DeviceResult:
    device: str
    operation: str
    platform: str
    status: ResultStatus
    data: Mapping[str, Any] | None
    duration_ms: int
    error: OperationError | None = None
    unsupported_fields: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "device": self.device,
            "operation": self.operation,
            "platform": self.platform,
            "status": self.status,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "unsupported_fields": list(self.unsupported_fields),
        }
        if self.error is None:
            return result
        result["error"] = {
            "code": self.error.code.value,
            "message": self.error.message,
        }
        return result


class ExecutionError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
