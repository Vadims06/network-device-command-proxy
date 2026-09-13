"""Cross-check the proxy's own BGP neighbor detail parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_bgp = pytest.importorskip("genie.libs.parser.iosxr.show_bgp")

import device_command_proxy
from device_command_proxy.platforms.iosxr.bgp_neighbor_detail_parser import (
    parse_bgp_neighbor_detail,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_fixture_agrees_with_genie_on_neighbor_identity_and_state():
    output = _read_fixture("show_bgp_instance_neighbors_detail.txt")
    genie_result = genie_show_bgp.ShowBgpInstanceNeighborsDetail(device=None).parse(
        output=output
    )
    ours = parse_bgp_neighbor_detail(output)

    genie_neighbors = genie_result["instance"]["all"]["vrf"]["default"]["neighbor"]
    assert [n["neighbor"] for n in ours["neighbors"]] == list(genie_neighbors)
    for neighbor in ours["neighbors"]:
        genie_neighbor = genie_neighbors[neighbor["neighbor"]]
        assert neighbor["remote_as"] == genie_neighbor["remote_as"]
        assert neighbor["remote_router_id"] == genie_neighbor["router_id"]
        assert neighbor["up_time"] == genie_neighbor["up_time"]
        assert neighbor["hold_time_sec"] == genie_neighbor["holdtime"]
        assert neighbor["keepalive_interval_sec"] == genie_neighbor["keepalive_interval"]
        assert neighbor["state"].lower() == genie_neighbor["session_state"]
