"""Static, file-backed inventory for standalone use without NetBox.

Satisfies the same InventoryProvider protocol as NetBoxInventoryProvider, so
main.py can pick either at startup depending on which is configured.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError
from device_command_proxy.json_files import reject_duplicate_keys
from device_command_proxy.validation import validate_devices


_KNOWN_ENTRY_FIELDS = frozenset(
    {"host", "port", "platform", "credential_profile", "interfaces"}
)


class StaticInventoryProvider:
    def __init__(
        self,
        devices: Mapping[str, Mapping[str, Any]],
        *,
        supported_platforms: Iterable[str],
        credential_profiles: Iterable[str] | None,
    ):
        platforms = frozenset(supported_platforms)
        # None: the credential source resolves no profile names, so there is
        # nothing to check a device's credential_profile against.
        profiles = (
            None if credential_profiles is None else frozenset(credential_profiles)
        )
        if not platforms:
            raise ValueError("at least one supported platform is required")
        if profiles is not None and not profiles:
            raise ValueError("at least one credential profile is required")
        # A name the request path would reject makes the entry permanently
        # unreachable, so it is caught here rather than on every request.
        for name in devices:
            validate_devices((name,))
        self._devices = {
            name: _parse_device(name, entry, platforms, profiles)
            for name, entry in devices.items()
        }

    @classmethod
    def from_file(
        cls,
        inventory_path: str,
        *,
        supported_platforms: Iterable[str],
        credential_profiles: Iterable[str] | None,
    ) -> "StaticInventoryProvider":
        devices = json.loads(
            Path(inventory_path).read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
        return cls(
            devices,
            supported_platforms=supported_platforms,
            credential_profiles=credential_profiles,
        )

    def get_device(self, device_name: str) -> DeviceProfile:
        device = self._devices.get(device_name)
        if device is None:
            raise ExecutionError(ErrorCode.DEVICE_NOT_FOUND, "device not found")
        return device


def _parse_device(
    name: str,
    entry: Mapping[str, Any],
    supported_platforms: frozenset[str],
    credential_profiles: frozenset[str] | None,
) -> DeviceProfile:
    try:
        unknown_fields = set(entry) - _KNOWN_ENTRY_FIELDS
        if unknown_fields:
            # A misspelled field (e.g. "interface" instead of "interfaces")
            # would otherwise be silently ignored in favor of that field's
            # default, and the device would look configured while every
            # request against it fails.
            raise ValueError(f"unknown field(s): {sorted(unknown_fields)}")
        host = ipaddress.ip_address(_valid_string(entry["host"], "host"))
        if isinstance(host, ipaddress.IPv6Address):
            host = host.ipv4_mapped or host
        return DeviceProfile(
            name=name,
            host=str(host),
            port=_valid_port(entry.get("port", 22)),
            platform=_valid_name(entry["platform"], "platform", supported_platforms),
            credential_profile=_credential_profile(entry, credential_profiles),
        )
    except KeyError as exception:
        raise ValueError(
            f"static inventory entry for device '{name}' is missing {exception}"
        ) from exception
    except (TypeError, ValueError) as exception:
        # Naming the failed constraint is the point of validating at startup;
        # an operator should not have to read a traceback to fix a typo.
        raise ValueError(
            f"invalid static inventory entry for device '{name}': {exception}"
        ) from exception


def _credential_profile(
    entry: Mapping[str, Any], credential_profiles: frozenset[str] | None
) -> str:
    """Required only when something actually resolves it.

    With env credentials one login covers every device, so demanding a
    profile name would be asking for a value nothing reads.
    """
    if credential_profiles is not None:
        return _valid_name(
            entry["credential_profile"], "credential_profile", credential_profiles
        )
    if "credential_profile" not in entry:
        return ""
    return _valid_string(entry["credential_profile"], "credential_profile")


def _valid_name(value: Any, field_name: str, allowed: frozenset[str]) -> str:
    """Catch a typo while loading, not on the first request for the device.

    Both the driver registry and the credential-profile mapping are fixed
    once the app is built, so a name absent from either can never start
    working later.
    """
    name = _valid_string(value, field_name)
    if name not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
    return name


def _valid_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{field_name} must be a non-empty string")
    return value


def _valid_port(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("port must be an integer")
    if not 1 <= value <= 65535:
        raise ValueError("port must be between 1 and 65535")
    return value
