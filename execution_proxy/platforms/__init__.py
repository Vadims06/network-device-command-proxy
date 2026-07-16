"""Explicit per-vendor adapter registry (no auto-discovery)."""

from __future__ import annotations

from execution_proxy.platforms.frr.driver import create_adapter as create_frr_adapter
from execution_proxy.platforms.junos.driver import create_adapter as create_junos_adapter

PLATFORMS = {"frr": create_frr_adapter, "junos": create_junos_adapter}
