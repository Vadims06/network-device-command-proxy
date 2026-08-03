"""FRR semantic operation adapter and Scrapli driver creation."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Iterator

from scrapli.driver.generic import GenericDriver

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
    ensure_host_key,
    KNOWN_HOSTS_FILE_ENV,
)


@contextmanager
def create_frr_driver(
    device: DeviceProfile,
    credentials: DeviceCredentials,
    *,
    known_hosts_file: str | None = None,
    private_key_directory: str | None = None,
) -> Iterator[GenericDriver]:
    if known_hosts_file is None:
        known_hosts_file = os.environ.get(KNOWN_HOSTS_FILE_ENV, "").strip() or None
    driver_options = {
        "auth_strict_key": known_hosts_file is not None,
    }
    if known_hosts_file is not None:
        ensure_host_key(device.host, device.port, known_hosts_file)
        driver_options["ssh_known_hosts_file"] = known_hosts_file
    with authentication_options(
        credentials,
        private_key_directory=private_key_directory,
    ) as authentication:
        driver = GenericDriver(
            host=device.host,
            port=device.port,
            auth_username=credentials.username,
            timeout_socket=5.0,
            timeout_transport=10.0,
            timeout_ops=10.0,
            transport="system",
            comms_prompt_pattern=r"^[a-zA-Z0-9_.-]+[>#]\s*$",
            channel_log=False,
            **driver_options,
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


UNSUPPORTED_FIELDS: dict[Operation, tuple[str, ...]] = {}


class FrrAdapter(DeviceAdapter):
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
        payload = self._send_command("show ip ospf neighbor json")
        neighbors = []
        for router_id, neighbor_list in payload.get("neighbors", {}).items():
            for neighbor in neighbor_list:
                neighbors.append(
                    OspfNeighbor(
                        router_id=router_id,
                        adjacency_state=neutral.adjacency_state(
                            neighbor.get("nbrState")
                        ),
                        state_raw=neutral.raw_text(neighbor.get("nbrState")),
                        role=neutral.router_role(
                            neighbor.get("role") or neighbor.get("nbrState")
                        ),
                        interface=str(neighbor.get("ifaceName", "")).split(":", 1)[0],
                        peer_address=neighbor.get("ifaceAddress"),
                        dead_time_ms=neighbor.get("routerDeadIntervalTimerDueMsec"),
                    )
                )
        return OspfNeighbors(instance=payload.get("ospfInstance"), neighbors=neighbors)

    def _get_ospf_neighbor_detail(self) -> OspfNeighborDetails:
        payload = self._send_command("show ip ospf neighbor detail json")
        neighbors = []
        for router_id, neighbor_list in payload.get("neighbors", {}).items():
            for neighbor in neighbor_list:
                neighbors.append(
                    OspfNeighborDetail(
                        router_id=router_id,
                        adjacency_state=neutral.adjacency_state(
                            neighbor.get("nbrState")
                        ),
                        state_raw=neutral.raw_text(neighbor.get("nbrState")),
                        role=neutral.router_role(
                            neighbor.get("role") or neighbor.get("nbrState")
                        ),
                        area=neighbor.get("areaId"),
                        interface=neighbor.get("ifaceName"),
                        peer_address=neighbor.get("ifaceAddress"),
                        dead_time_ms=neighbor.get("routerDeadIntervalTimerDueMsec"),
                        state_changes=neighbor.get("stateChangeCounter"),
                    )
                )
        return OspfNeighborDetails(
            instance=payload.get("ospfInstance"), neighbors=neighbors
        )

    def _get_interface_status(self, *, interface: str) -> InterfaceStatus:
        payload = self._send_command(f"show interface {interface} json")
        interface_payload = payload[interface]
        return InterfaceStatus(
            interface=interface,
            admin_up=interface_payload.get("administrativeStatus") == "up",
            oper_up=interface_payload.get("operationalStatus") == "up",
            addresses=[
                address["address"]
                for address in interface_payload.get("ipAddresses", [])
            ],
            mtu=interface_payload.get("mtu"),
            speed_mbps=interface_payload.get("speed"),
        )

    def _get_ospf_interface(self, *, interface: str) -> OspfInterfaces:
        return self._get_ospf_interfaces(interface=interface)

    def _get_ospf_interfaces(self, *, interface: str | None = None) -> OspfInterfaces:
        command = "show ip ospf interface"
        if interface is not None:
            command += f" {interface}"
        command += " json"
        payload = self._send_command(command)
        entries = []
        for interface_name, interface_payload in sorted(
            payload.get("interfaces", {}).items()
        ):
            if interface is not None and interface_name != interface:
                continue
            entries.append(
                OspfInterface(
                    interface=interface_name,
                    up=interface_payload.get("ifUp"),
                    enabled=interface_payload.get("ospfEnabled"),
                    state=interface_payload.get("state"),
                    network_type=neutral.network_type(
                        interface_payload.get("networkType")
                    ),
                    network_type_raw=neutral.raw_text(
                        interface_payload.get("networkType")
                    ),
                    area=interface_payload.get("area"),
                    cost=interface_payload.get("cost"),
                    hello_interval_ms=interface_payload.get("timerMsecs"),
                    dead_interval_sec=interface_payload.get("timerDeadSecs"),
                    neighbors=interface_payload.get("nbrCount"),
                    adjacent_neighbors=interface_payload.get("nbrAdjacentCount"),
                )
            )
        return OspfInterfaces(interfaces=entries)

    def _get_ospf_status(self) -> OspfStatus:
        payload = self._send_command("show ip ospf json")
        areas = [
            OspfArea(
                area=area_id,
                active_interfaces=area_payload.get("areaIfActiveCounter"),
                full_neighbors=area_payload.get("nbrFullAdjacentCounter"),
                spf_runs=area_payload.get("spfExecutedCounter"),
                lsa_count=area_payload.get("lsaNumber"),
            )
            for area_id, area_payload in sorted(payload.get("areas", {}).items())
        ]
        return OspfStatus(
            instance=payload.get("ospfInstance"),
            router_id=payload.get("routerId"),
            areas=areas,
        )

    def _get_route(self, *, prefix: str) -> RouteLookup:
        payload = self._send_command(f"show ip route {prefix} json")
        matched_prefix, route_entries = next(
            ((key, entries) for key, entries in payload.items() if entries),
            (None, []),
        )
        routes = []
        for route_entry in route_entries:
            routes.append(
                Route(
                    protocol=route_entry.get("protocol"),
                    selected=route_entry.get("selected", False),
                    distance=route_entry.get("distance"),
                    metric=route_entry.get("metric"),
                    next_hops=[
                        RouteNextHop(
                            address=next_hop.get("ip"),
                            interface=next_hop.get("interfaceName"),
                            active=next_hop.get("active", False),
                        )
                        for next_hop in route_entry.get("nexthops", [])
                    ],
                )
            )
        return RouteLookup(
            prefix=prefix,
            matched_prefix=matched_prefix,
            found=bool(routes),
            routes=routes,
        )
