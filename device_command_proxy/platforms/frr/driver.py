"""FRR semantic operation adapter and Scrapli driver creation."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from scrapli.driver.generic import GenericDriver

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile
from device_command_proxy.platforms.base import DeviceAdapter
from device_command_proxy.ssh_auth import authentication_options, ensure_host_key


@contextmanager
def create_frr_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str = "/var/lib/execution-proxy/known_hosts",
    private_key_directory: str = "/run/execution-proxy",
) -> Iterator[GenericDriver]:
    ensure_host_key(device.host, device.port, known_hosts_file)
    with authentication_options(
        credentials,
        private_key_directory=private_key_directory,
    ) as authentication:
        driver = GenericDriver(
            host=device.host,
            port=device.port,
            auth_username=credentials.username,
            auth_strict_key=True,
            ssh_known_hosts_file=known_hosts_file,
            timeout_socket=5.0,
            timeout_transport=10.0,
            timeout_ops=10.0,
            transport="system",
            comms_prompt_pattern=r"^[a-zA-Z0-9_.-]+[>#]\s*$",
            channel_log=False,
            **authentication,
        )
        try:
            driver.open()
            yield driver
        finally:
            if driver.isalive():
                driver.close()


def create_adapter(device: DeviceProfile, credentials: DeviceCredentials) -> "FrrAdapter":
    return FrrAdapter(lambda: create_frr_driver(device, credentials))


class FrrAdapter(DeviceAdapter):
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
        return "show ip ospf neighbor json", _normalize_neighbors

    def _get_ospf_neighbor_detail(self):
        return "show ip ospf neighbor detail json", _normalize_neighbor_details

    def _get_interface_status(self, *, interface: str):
        return f"show interface {interface} json", lambda payload: _normalize_interface(
            payload, interface
        )

    def _get_ospf_interface(self, *, interface: str):
        return (
            f"show ip ospf interface {interface} json",
            lambda payload: _normalize_ospf_interface(payload, interface),
        )

    def _get_ospf_status(self):
        return "show ip ospf json", _normalize_ospf_status

    def _get_route(self, *, prefix: str):
        return f"show ip route {prefix} json", lambda payload: _normalize_route(
            payload, prefix
        )


def _flatten_neighbors(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (router_id, neighbor)
        for router_id, neighbors in payload.get("neighbors", {}).items()
        for neighbor in neighbors
    ]


def _normalize_neighbors(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": payload.get("ospfInstance"),
        "neighbors": [
            {
                "router_id": router_id,
                "state": neighbor.get("nbrState"),
                "role": neighbor.get("role"),
                "interface": str(neighbor.get("ifaceName", "")).split(":", 1)[0],
                "peer_address": neighbor.get("ifaceAddress"),
                "dead_time_ms": neighbor.get("routerDeadIntervalTimerDueMsec"),
            }
            for router_id, neighbor in _flatten_neighbors(payload)
        ],
    }


def _normalize_neighbor_details(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": payload.get("ospfInstance"),
        "neighbors": [
            {
                "router_id": router_id,
                "state": neighbor.get("nbrState"),
                "role": neighbor.get("role"),
                "area": neighbor.get("areaId"),
                "interface": neighbor.get("ifaceName"),
                "peer_address": neighbor.get("ifaceAddress"),
                "dead_time_ms": neighbor.get("routerDeadIntervalTimerDueMsec"),
                "state_changes": neighbor.get("stateChangeCounter"),
            }
            for router_id, neighbor in _flatten_neighbors(payload)
        ],
    }


def _normalize_interface(payload: dict[str, Any], interface: str) -> dict[str, Any]:
    interface_data = payload[interface]
    return {
        "interface": interface,
        "admin_up": interface_data.get("administrativeStatus") == "up",
        "oper_up": interface_data.get("operationalStatus") == "up",
        "addresses": [
            address["address"] for address in interface_data.get("ipAddresses", [])
        ],
        "mtu": interface_data.get("mtu"),
        "speed_mbps": interface_data.get("speed"),
    }


def _normalize_ospf_interface(payload: dict[str, Any], interface: str) -> dict[str, Any]:
    interface_data = payload["interfaces"][interface]
    return {
        "interface": interface,
        "up": interface_data.get("ifUp"),
        "enabled": interface_data.get("ospfEnabled"),
        "state": interface_data.get("state"),
        "network_type": interface_data.get("networkType"),
        "area": interface_data.get("area"),
        "cost": interface_data.get("cost"),
        "hello_interval_ms": interface_data.get("timerMsecs"),
        "dead_interval_sec": interface_data.get("timerDeadSecs"),
        "neighbors": interface_data.get("nbrCount"),
        "adjacent_neighbors": interface_data.get("nbrAdjacentCount"),
    }


def _normalize_ospf_status(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "instance": payload.get("ospfInstance"),
        "router_id": payload.get("routerId"),
        "areas": [
            {
                "area": area_id,
                "active_interfaces": area.get("areaIfActiveCounter"),
                "full_neighbors": area.get("nbrFullAdjacentCounter"),
                "spf_runs": area.get("spfExecutedCounter"),
                "lsa_count": area.get("lsaNumber"),
            }
            for area_id, area in sorted(payload.get("areas", {}).items())
        ],
    }


def _normalize_route(payload: dict[str, Any], prefix: str) -> dict[str, Any]:
    routes = payload.get(prefix, [])
    return {
        "prefix": prefix,
        "found": bool(routes),
        "routes": [
            {
                "protocol": route.get("protocol"),
                "selected": route.get("selected", False),
                "distance": route.get("distance"),
                "metric": route.get("metric"),
                "next_hops": [
                    {
                        "address": next_hop.get("ip"),
                        "interface": next_hop.get("interfaceName"),
                        "active": next_hop.get("active", False),
                    }
                    for next_hop in route.get("nexthops", [])
                ],
            }
            for route in routes
        ],
    }
