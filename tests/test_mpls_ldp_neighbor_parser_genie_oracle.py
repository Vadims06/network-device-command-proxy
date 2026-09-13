"""Cross-check the proxy's own MPLS LDP neighbor parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_mpls = pytest.importorskip("genie.libs.parser.iosxr.show_mpls")

import device_command_proxy
from device_command_proxy.platforms.iosxr.mpls_ldp_neighbor_parser import (
    parse_mpls_ldp_neighbor_detail,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def _genie_peers_by_identifier(genie_result):
    peers = {}
    for vrf_data in genie_result["vrf"].values():
        for peer_ip, peer_data in vrf_data["peers"].items():
            for label_space, detail in peer_data["label_space_id"].items():
                peers[f"{peer_ip}:{label_space}"] = detail
    return peers


def test_fixture_agrees_with_genie_on_peer_identity_and_state():
    output = _read_fixture("show_mpls_ldp_neighbor_detail.txt")
    ours = parse_mpls_ldp_neighbor_detail(output)
    genie_result = genie_show_mpls.ShowMplsLdpNeighborDetail(device=None).parse(output=output)
    genie_peers = _genie_peers_by_identifier(genie_result)

    assert {n["peer_ldp_identifier"] for n in ours["neighbors"]} == set(genie_peers)
    for neighbor in ours["neighbors"]:
        genie_peer = genie_peers[neighbor["peer_ldp_identifier"]]
        assert neighbor["state"] == genie_peer["state"]
        assert neighbor["up_time"] == genie_peer["uptime"]
        assert neighbor["session_holdtime_sec"] == genie_peer["session_holdtime"]
        assert neighbor["messages_sent"] == genie_peer["msg_sent"]
        assert neighbor["messages_received"] == genie_peer["msg_rcvd"]
