"""Explicit per-vendor adapter registry (no auto-discovery)."""

from __future__ import annotations

from device_command_proxy.platforms.frr.driver import UNSUPPORTED_FIELDS as FRR_UNSUPPORTED
from device_command_proxy.platforms.frr.driver import create_adapter as create_frr_adapter
from device_command_proxy.platforms.iosxr.driver import UNSUPPORTED_FIELDS as IOSXR_UNSUPPORTED
from device_command_proxy.platforms.iosxr.driver import create_adapter as create_iosxr_adapter
from device_command_proxy.platforms.junos.driver import UNSUPPORTED_FIELDS as JUNOS_UNSUPPORTED
from device_command_proxy.platforms.junos.driver import create_adapter as create_junos_adapter

PLATFORMS = {
    "frr": create_frr_adapter,
    "junos": create_junos_adapter,
    "iosxr": create_iosxr_adapter,
}

# Static capability metadata, deliberately not adapter state: what a vendor's
# CLI can never report does not depend on whether one command succeeded, so it
# must also be reportable on failures, where no adapter was ever built.
UNSUPPORTED_FIELDS = {
    "frr": FRR_UNSUPPORTED,
    "junos": JUNOS_UNSUPPORTED,
    "iosxr": IOSXR_UNSUPPORTED,
}
