"""Explicit per-vendor adapter registry (no auto-discovery)."""

from __future__ import annotations

from device_command_proxy.platforms.frr.driver import create_adapter as create_frr_adapter
from device_command_proxy.platforms.junos.driver import create_adapter as create_junos_adapter

PLATFORMS = {"frr": create_frr_adapter, "junos": create_junos_adapter}
