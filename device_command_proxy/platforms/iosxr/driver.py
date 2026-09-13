"""IOS XR semantic operation adapter and Scrapli driver creation.

First text-parsing platform in the proxy (both frr and junos consume
structured JSON); see docs/rsvp-parsing.md.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator

from scrapli.driver.generic import GenericDriver

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile, Transport
from device_command_proxy.fixture_driver import create_fixture_driver
from device_command_proxy.operation_types import Operation
from device_command_proxy.platforms.base import DeviceAdapter, OutputFormat
from device_command_proxy.platforms.iosxr.bgp_neighbor_detail_parser import (
    parse_bgp_neighbor_detail,
)
from device_command_proxy.platforms.iosxr.bgp_summary_parser import parse_bgp_instance_summary
from device_command_proxy.platforms.iosxr.isis_database_parser import (
    parse_isis_database_detail,
)
from device_command_proxy.platforms.iosxr.isis_interface_parser import parse_isis_interface
from device_command_proxy.platforms.iosxr.isis_neighbors_parser import parse_isis_neighbors
from device_command_proxy.platforms.iosxr.mpls_forwarding_parser import parse_mpls_forwarding
from device_command_proxy.platforms.iosxr.mpls_ldp_neighbor_parser import (
    parse_mpls_ldp_neighbor_detail,
)
from device_command_proxy.platforms.iosxr.rsvp_parser import parse_rsvp_session_detail
from device_command_proxy.platforms.iosxr.vrf_parser import parse_vrf_all_detail
from device_command_proxy.schemas import (
    BgpNeighborDetails,
    BgpSummary,
    IsisDatabase,
    IsisInterfaces,
    IsisNeighbors,
    MplsForwardingTable,
    MplsLdpNeighbors,
    RsvpLspInventory,
    VrfInventory,
)
from device_command_proxy.ssh_auth import (
    authentication_options,
    ensure_host_key,
    KNOWN_HOSTS_FILE_ENV,
)


@contextmanager
def create_iosxr_driver(
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
            # IOS XR prompt: "RP/0/RP0/CPU0:hostname#" (or "(config)#" etc,
            # not needed here - read-only operations only).
            comms_prompt_pattern=r"^RP/\S+:[a-zA-Z0-9_.-]+[#>]\s*$",
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


def create_adapter(device: DeviceProfile, credentials: DeviceCredentials) -> "IosxrAdapter":
    if device.transport is Transport.FIXTURE:
        return IosxrAdapter(lambda: create_fixture_driver(device.name))
    return IosxrAdapter(lambda: create_iosxr_driver(device, credentials))


# No field in RsvpLspInventory is structurally unreportable via this command;
# every field is either populated or a legitimate "No intf"/"No label"/empty
# value the device itself reports (see docs/rsvp-parsing.md).
UNSUPPORTED_FIELDS: dict[Operation, tuple[str, ...]] = {}


class IosxrAdapter(DeviceAdapter):
    def __init__(self, driver_factory):
        super().__init__(driver_factory)
        self._operation_handlers = {
            Operation.GET_RSVP_LSPS: self._get_rsvp_lsps,
            Operation.GET_VRF_DETAIL: self._get_vrf_detail,
            Operation.GET_BGP_SUMMARY: self._get_bgp_summary,
            Operation.GET_BGP_NEIGHBOR_DETAIL: self._get_bgp_neighbor_detail,
            Operation.GET_ISIS_NEIGHBORS: self._get_isis_neighbors,
            Operation.GET_ISIS_INTERFACE: self._get_isis_interface,
            Operation.GET_ISIS_DATABASE: self._get_isis_database,
            Operation.GET_MPLS_FORWARDING: self._get_mpls_forwarding,
            Operation.GET_LDP_NEIGHBORS: self._get_ldp_neighbors,
        }

    def _get_rsvp_lsps(self) -> RsvpLspInventory:
        output = self._send_command(
            "show rsvp session detail", output_format=OutputFormat.TEXT
        )
        return parse_rsvp_session_detail(output)

    def _get_vrf_detail(self) -> VrfInventory:
        output = self._send_command("show vrf all detail", output_format=OutputFormat.TEXT)
        return parse_vrf_all_detail(output)

    def _get_bgp_summary(self) -> BgpSummary:
        output = self._send_command(
            "show bgp instance all all all summary", output_format=OutputFormat.TEXT
        )
        return parse_bgp_instance_summary(output)

    def _get_bgp_neighbor_detail(self) -> BgpNeighborDetails:
        output = self._send_command(
            "show bgp instance all all all neighbors detail",
            output_format=OutputFormat.TEXT,
        )
        return parse_bgp_neighbor_detail(output)

    def _get_isis_neighbors(self) -> IsisNeighbors:
        output = self._send_command("show isis neighbors", output_format=OutputFormat.TEXT)
        return parse_isis_neighbors(output)

    def _get_isis_interface(self) -> IsisInterfaces:
        output = self._send_command("show isis interface", output_format=OutputFormat.TEXT)
        return parse_isis_interface(output)

    def _get_isis_database(self) -> IsisDatabase:
        output = self._send_command(
            "show isis database detail", output_format=OutputFormat.TEXT
        )
        return parse_isis_database_detail(output)

    def _get_mpls_forwarding(self) -> MplsForwardingTable:
        output = self._send_command("show mpls forwarding", output_format=OutputFormat.TEXT)
        return parse_mpls_forwarding(output)

    def _get_ldp_neighbors(self) -> MplsLdpNeighbors:
        output = self._send_command(
            "show mpls ldp neighbor detail", output_format=OutputFormat.TEXT
        )
        return parse_mpls_ldp_neighbor_detail(output)
