"""Cross-check the proxy's own BGP summary parser against Genie's independent
parse of the same fixture. Requires the optional `genie` dependency group;
skipped otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_bgp = pytest.importorskip("genie.libs.parser.iosxr.show_bgp")

import device_command_proxy
from device_command_proxy.platforms.iosxr.bgp_summary_parser import parse_bgp_instance_summary

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_fixture_agrees_with_genie_on_neighbors_and_router_id():
    output = _read_fixture("show_bgp_instance_summary.txt")
    genie_result = genie_show_bgp.ShowBgpInstanceSummary(device=None).parse(output=output)
    ours = parse_bgp_instance_summary(output)

    genie_default_vrf = genie_result["instance"]["default"]["vrf"]["default"]
    for family in ours["address_families"]:
        genie_family = genie_default_vrf["address_family"][family["address_family"]]
        assert family["router_id"] == genie_family["router_id"]
        assert family["local_as"] == genie_family["local_as"]

        genie_neighbors = genie_default_vrf["neighbor"]
        assert [n["neighbor"] for n in family["neighbors"]] == list(genie_neighbors)
        for neighbor in family["neighbors"]:
            genie_neighbor = genie_neighbors[neighbor["neighbor"]]
            genie_neighbor_af = genie_neighbor["address_family"][family["address_family"]]
            assert neighbor["remote_as"] == genie_neighbor["remote_as"]
            assert neighbor["messages_received"] == genie_neighbor_af["msg_rcvd"]
            assert neighbor["messages_sent"] == genie_neighbor_af["msg_sent"]
            assert neighbor["up_down"] == genie_neighbor_af["up_down"]
