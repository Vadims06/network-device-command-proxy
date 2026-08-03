"""Junos semantic operation adapter and Scrapli driver creation."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from scrapli.driver.core import JunosDriver

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile
from device_command_proxy.operation_types import Operation
from device_command_proxy.platforms import neutral
from device_command_proxy.platforms.base import DeviceAdapter
from device_command_proxy.schemas import (
    InterfaceStatus,
    OspfArea,
    OspfInterface,
    OspfInterfaces,
    OspfNeighbor,
    OspfNeighborDetail,
    OspfNeighborDetails,
    OspfNeighbors,
    OspfStatus,
    Route,
    RouteLookup,
    RouteNextHop,
)
from device_command_proxy.ssh_auth import (
    authentication_options,
    runtime_path_from_environment,
    ensure_host_key,
    KNOWN_HOSTS_FILE_ENV,
)


UNSUPPORTED_FIELDS: dict[Operation, tuple[str, ...]] = {
    Operation.GET_OSPF_NEIGHBORS: ("instance", "role"),
    Operation.GET_OSPF_NEIGHBOR_DETAIL: ("instance", "role", "state_changes"),
    Operation.GET_OSPF_INTERFACE: ("adjacent_neighbors",),
    Operation.GET_OSPF_INTERFACES: ("adjacent_neighbors",),
    Operation.GET_OSPF_STATUS: ("instance", "spf_runs", "lsa_count"),
}


@contextmanager
def create_junos_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str | None = None,
    private_key_directory: str | None = None,
) -> Iterator[JunosDriver]:
    if known_hosts_file is None:
        known_hosts_file = runtime_path_from_environment(KNOWN_HOSTS_FILE_ENV)
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
            Operation.GET_OSPF_NEIGHBORS: self._get_ospf_neighbors,
            Operation.GET_OSPF_NEIGHBOR_DETAIL: self._get_ospf_neighbor_detail,
            Operation.GET_INTERFACE_STATUS: self._get_interface_status,
            Operation.GET_OSPF_INTERFACE: self._get_ospf_interface,
            Operation.GET_OSPF_INTERFACES: self._get_ospf_interfaces,
            Operation.GET_OSPF_STATUS: self._get_ospf_status,
            Operation.GET_ROUTE: self._get_route,
        }

    def _get_ospf_neighbors(self) -> OspfNeighbors:
        payload = self._send_command("show ospf neighbor | display json")
        root = _items(payload, "ospf-neighbor-information")
        neighbor_entries = _items(root[0], "ospf-neighbor") if root else []
        neighbors = [
            OspfNeighbor(
                router_id=_field(neighbor, "neighbor-id"),
                adjacency_state=neutral.adjacency_state(
                    _field(neighbor, "ospf-neighbor-state")
                ),
                state_raw=neutral.raw_text(_field(neighbor, "ospf-neighbor-state")),
                role=None,
                interface=_field(neighbor, "interface-name"),
                peer_address=_field(neighbor, "neighbor-address"),
                dead_time_ms=self._to_milliseconds(
                    _field(neighbor, "activity-timer")
                ),
            )
            for neighbor in neighbor_entries
        ]
        return OspfNeighbors(instance=None, neighbors=neighbors)

    def _get_ospf_neighbor_detail(self) -> OspfNeighborDetails:
        payload = self._send_command("show ospf neighbor detail | display json")
        root = _items(payload, "ospf-neighbor-information")
        neighbor_entries = _items(root[0], "ospf-neighbor") if root else []
        neighbors = [
            OspfNeighborDetail(
                router_id=_field(neighbor, "neighbor-id"),
                adjacency_state=neutral.adjacency_state(
                    _field(neighbor, "ospf-neighbor-state")
                ),
                state_raw=neutral.raw_text(_field(neighbor, "ospf-neighbor-state")),
                role=None,
                area=_field(neighbor, "ospf-area"),
                interface=_field(neighbor, "interface-name"),
                peer_address=_field(neighbor, "neighbor-address"),
                dead_time_ms=self._to_milliseconds(
                    _field(neighbor, "activity-timer")
                ),
                state_changes=None,
            )
            for neighbor in neighbor_entries
        ]
        return OspfNeighborDetails(instance=None, neighbors=neighbors)

    def _get_interface_status(self, *, interface: str) -> InterfaceStatus:
        payload = self._send_command(
            f"show interfaces {interface} | display json"
        )
        root = _items(payload, "interface-information")
        physical_interfaces = _items(root[0], "physical-interface") if root else []
        if not physical_interfaces:
            raise KeyError(interface)
        physical_interface = physical_interfaces[0]
        addresses = [
            _field(address, "ifa-local")
            for logical_interface in _items(physical_interface, "logical-interface")
            for address_family in _items(logical_interface, "address-family")
            for address in _items(address_family, "interface-address")
            if _field(address, "ifa-local")
        ]
        speed = _field(physical_interface, "speed")
        speed_mbps = None
        if isinstance(speed, str) and speed.lower().endswith("mbps"):
            speed_mbps = int(speed[:-4])
        return InterfaceStatus(
            interface=interface,
            admin_up=_field(physical_interface, "admin-status") == "up",
            oper_up=_field(physical_interface, "oper-status") == "up",
            addresses=addresses,
            mtu=self._to_integer(_field(physical_interface, "mtu")),
            speed_mbps=speed_mbps,
        )

    def _get_ospf_interface(self, *, interface: str) -> OspfInterfaces:
        return self._get_ospf_interfaces(interface=interface)

    def _get_ospf_interfaces(self, *, interface: str | None = None) -> OspfInterfaces:
        command = "show ospf interface"
        if interface is not None:
            command += f" {interface}"
        payload = self._send_command(f"{command} detail | display json")
        root = _items(payload, "ospf-interface-information")
        entries = _items(root[0], "ospf-interface") if root else []
        interfaces = []
        for ospf_interface in entries:
            interface_state = _field(ospf_interface, "ospf-interface-state")
            interface_type = _field(ospf_interface, "interface-type")
            interfaces.append(
                OspfInterface(
                    interface=_field(ospf_interface, "interface-name"),
                    up=interface_state not in (None, "Down"),
                    enabled=True,
                    state=interface_state,
                    network_type=neutral.network_type(interface_type),
                    network_type_raw=neutral.raw_text(interface_type),
                    area=_field(ospf_interface, "ospf-area"),
                    cost=self._to_integer(
                        _field(ospf_interface, "ospf-interface-cost")
                    ),
                    hello_interval_ms=self._to_milliseconds(
                        _field(ospf_interface, "hello-interval")
                    ),
                    dead_interval_sec=self._to_integer(
                        _field(ospf_interface, "dead-interval")
                    ),
                    neighbors=self._to_integer(
                        _field(ospf_interface, "neighbor-count")
                    ),
                    adjacent_neighbors=None,
                )
            )
        return OspfInterfaces(interfaces=interfaces)

    def _get_ospf_status(self) -> OspfStatus:
        payload = self._send_command("show ospf overview | display json")
        root = _items(payload, "ospf-overview-information")
        overview_entries = _items(root[0], "ospf-overview") if root else []
        overview = overview_entries[0] if overview_entries else {}
        areas = []
        for area in _items(overview, "ospf-area-overview"):
            neighbor_overview = _items(area, "ospf-nbr-overview")
            interface_overview = _items(area, "ospf-intf-overview")
            areas.append(
                OspfArea(
                    area=_field(area, "ospf-area"),
                    active_interfaces=self._to_integer(
                        _field(interface_overview[0], "ospf-intf-active-count")
                        if interface_overview
                        else None
                    ),
                    full_neighbors=self._to_integer(
                        _field(neighbor_overview[0], "ospf-nbr-up-count")
                        if neighbor_overview
                        else None
                    ),
                    spf_runs=None,
                    lsa_count=None,
                )
            )
        return OspfStatus(
            instance=None,
            router_id=_field(overview, "ospf-router-id"),
            areas=areas,
        )

    def _get_route(self, *, prefix: str) -> RouteLookup:
        payload = self._send_command(f"show route {prefix} | display json")
        root = _items(payload, "route-information")
        tables = _items(root[0], "route-table") if root else []
        route_entries = _items(tables[0], "rt") if tables else []
        matched_prefix = _field(route_entries[0], "rt-destination") if route_entries else None
        routes = []
        for route_entry in route_entries:
            entries = _items(route_entry, "rt-entry")
            route = entries[0] if entries else {}
            routes.append(
                Route(
                    protocol=_field(route, "protocol-name"),
                    selected="current-active" in route,
                    distance=self._to_integer(_field(route, "preference")),
                    metric=self._to_integer(_field(route, "metric")),
                    next_hops=[
                        RouteNextHop(
                            address=_field(next_hop, "to"),
                            interface=_field(next_hop, "via"),
                            active=True,
                        )
                        for next_hop in _items(route, "nh")
                    ],
                )
            )
        return RouteLookup(
            prefix=prefix,
            matched_prefix=matched_prefix,
            found=bool(routes),
            routes=routes,
        )

    @staticmethod
    def _to_integer(value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @classmethod
    def _to_milliseconds(cls, value: Any) -> int | None:
        seconds = cls._to_integer(value)
        if seconds is None:
            return None
        return seconds * 1000
