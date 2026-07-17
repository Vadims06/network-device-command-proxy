"""Junos semantic operation adapter and Scrapli driver creation.

Junos `| display json` wraps every leaf value as a single-element list of
`{"data": ...}` (an artifact of its XML-to-JSON conversion). `_field()`
unwraps that shape; every normalizer returns the same target schema as the
FRR adapter so the two vendors satisfy one shared contract.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from scrapli.driver.core import JunosDriver

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile
from device_command_proxy.platforms.base import DeviceAdapter
from device_command_proxy.ssh_auth import authentication_options, ensure_host_key


@contextmanager
def create_junos_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str = "/var/lib/execution-proxy/known_hosts",
    private_key_directory: str = "/run/execution-proxy",
) -> Iterator[JunosDriver]:
    ensure_host_key(device.host, device.port, known_hosts_file)
    with authentication_options(
        credentials,
        private_key_directory=private_key_directory,
    ) as authentication:
        driver = JunosDriver(
            host=device.host,
            port=device.port,
            auth_username=credentials.username,
            auth_strict_key=True,
            ssh_known_hosts_file=known_hosts_file,
            timeout_socket=5.0,
            timeout_transport=10.0,
            timeout_ops=10.0,
            transport="system",
            channel_log=False,
            **authentication,
        )
        try:
            driver.open()
            yield driver
        finally:
            if driver.isalive():
                driver.close()


def create_adapter(device: DeviceProfile, credentials: DeviceCredentials) -> "JunosAdapter":
    return JunosAdapter(lambda: create_junos_driver(device, credentials))


def _field(node: dict[str, Any], key: str, default: Any = None) -> Any:
    values = node.get(key)
    if not values:
        return default
    return values[0].get("data", default)


def _items(node: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return node.get(key) or []


class JunosAdapter(DeviceAdapter):
    def __init__(self, driver_factory):
        super().__init__(driver_factory)
        self._operation_handlers = {
            "get_ospf_neighbors": self._get_ospf_neighbors,
            "get_ospf_neighbor_detail": self._get_ospf_neighbor_detail,
            "get_interface_status": self._get_interface_status,
            "get_ospf_interface": self._get_ospf_interface,
            "get_ospf_status": self._get_ospf_status,
            "get_route": self._get_route,
        }

    def _get_ospf_neighbors(self):
        return "show ospf neighbor | display json", _normalize_neighbors

    def _get_ospf_neighbor_detail(self):
        return "show ospf neighbor detail | display json", _normalize_neighbor_details

    def _get_interface_status(self, *, interface: str):
        return (
            f"show interfaces {interface} | display json",
            lambda payload: _normalize_interface(payload, interface),
        )

    def _get_ospf_interface(self, *, interface: str):
        return (
            f"show ospf interface {interface} detail | display json",
            lambda payload: _normalize_ospf_interface(payload, interface),
        )

    def _get_ospf_status(self):
        return "show ospf overview | display json", _normalize_ospf_status

    def _get_route(self, *, prefix: str):
        return (
            f"show route {prefix} | display json",
            lambda payload: _normalize_route(payload, prefix),
        )


def _neighbor_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    root = _items(payload, "ospf-neighbor-information")
    if not root:
        return []
    return _items(root[0], "ospf-neighbor")


def _normalize_neighbors(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": None,
        "neighbors": [
            {
                "router_id": _field(neighbor, "neighbor-id"),
                "state": _field(neighbor, "ospf-neighbor-state"),
                "role": None,
                "interface": _field(neighbor, "interface-name"),
                "peer_address": _field(neighbor, "neighbor-address"),
                "dead_time_ms": _to_ms(_field(neighbor, "activity-timer")),
            }
            for neighbor in _neighbor_entries(payload)
        ],
    }


def _normalize_neighbor_details(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": None,
        "neighbors": [
            {
                "router_id": _field(neighbor, "neighbor-id"),
                "state": _field(neighbor, "ospf-neighbor-state"),
                "role": None,
                "area": _field(neighbor, "ospf-area"),
                "interface": _field(neighbor, "interface-name"),
                "peer_address": _field(neighbor, "neighbor-address"),
                "dead_time_ms": _to_ms(_field(neighbor, "activity-timer")),
                "state_changes": None,
            }
            for neighbor in _neighbor_entries(payload)
        ],
    }


def _normalize_interface(payload: dict[str, Any], interface: str) -> dict[str, Any]:
    root = _items(payload, "interface-information")
    physical = _items(root[0], "physical-interface") if root else []
    if not physical:
        raise KeyError(interface)
    physical_interface = physical[0]
    addresses = [
        _field(address, "ifa-local")
        for logical in _items(physical_interface, "logical-interface")
        for family in _items(logical, "address-family")
        for address in _items(family, "interface-address")
        if _field(address, "ifa-local")
    ]
    speed = _field(physical_interface, "speed")
    speed_mbps = None
    if isinstance(speed, str) and speed.lower().endswith("mbps"):
        speed_mbps = int(speed[:-4])
    return {
        "interface": interface,
        "admin_up": _field(physical_interface, "admin-status") == "up",
        "oper_up": _field(physical_interface, "oper-status") == "up",
        "addresses": addresses,
        "mtu": _to_int(_field(physical_interface, "mtu")),
        "speed_mbps": speed_mbps,
    }


def _normalize_ospf_interface(payload: dict[str, Any], interface: str) -> dict[str, Any]:
    root = _items(payload, "ospf-interface-information")
    entries = _items(root[0], "ospf-interface") if root else []
    if not entries:
        raise KeyError(interface)
    ospf_interface = entries[0]
    return {
        "interface": interface,
        "up": _field(ospf_interface, "ospf-interface-state") not in (None, "Down"),
        "enabled": True,
        "state": _field(ospf_interface, "ospf-interface-state"),
        "network_type": _field(ospf_interface, "interface-type"),
        "area": _field(ospf_interface, "ospf-area"),
        "cost": _to_int(_field(ospf_interface, "ospf-interface-cost")),
        "hello_interval_ms": _to_ms(_field(ospf_interface, "hello-interval")),
        "dead_interval_sec": _to_int(_field(ospf_interface, "dead-interval")),
        "neighbors": _to_int(_field(ospf_interface, "neighbor-count")),
        "adjacent_neighbors": _to_int(_field(ospf_interface, "neighbor-count")),
    }


def _normalize_ospf_status(payload: dict[str, Any]) -> dict[str, Any]:
    root = _items(payload, "ospf-overview-information")
    overview_list = _items(root[0], "ospf-overview") if root else []
    overview = overview_list[0] if overview_list else {}
    areas = []
    for area in _items(overview, "ospf-area-overview"):
        nbr_overview = _items(area, "ospf-nbr-overview")
        intf_overview = _items(area, "ospf-intf-overview")
        areas.append(
            {
                "area": _field(area, "ospf-area"),
                "active_interfaces": _to_int(
                    _field(intf_overview[0], "ospf-intf-active-count")
                    if intf_overview
                    else None
                ),
                "full_neighbors": _to_int(
                    _field(nbr_overview[0], "ospf-nbr-up-count") if nbr_overview else None
                ),
                "spf_runs": None,
                "lsa_count": None,
            }
        )
    return {
        "instance": None,
        "router_id": _field(overview, "ospf-router-id"),
        "areas": areas,
    }


def _normalize_route(payload: dict[str, Any], prefix: str) -> dict[str, Any]:
    root = _items(payload, "route-information")
    tables = _items(root[0], "route-table") if root else []
    routes = _items(tables[0], "rt") if tables else []
    normalized_routes = []
    for route in routes:
        entries = _items(route, "rt-entry")
        entry = entries[0] if entries else {}
        normalized_routes.append(
            {
                "protocol": _field(entry, "protocol-name"),
                "selected": "current-active" in entry,
                "distance": _to_int(_field(entry, "preference")),
                "metric": _to_int(_field(entry, "metric")),
                "next_hops": [
                    {
                        "address": _field(next_hop, "to"),
                        "interface": _field(next_hop, "via"),
                        "active": True,
                    }
                    for next_hop in _items(entry, "nh")
                ],
            }
        )
    return {
        "prefix": prefix,
        "found": bool(normalized_routes),
        "routes": normalized_routes,
    }


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_ms(value: Any) -> int | None:
    seconds = _to_int(value)
    if seconds is None:
        return None
    return seconds * 1000
