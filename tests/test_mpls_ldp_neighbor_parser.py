"""Literal-expectation tests for the IOS XR MPLS LDP neighbor parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

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


def test_single_peer_full_fields():
    result = parse_mpls_ldp_neighbor_detail(
        _read_fixture("show_mpls_ldp_neighbor_detail.txt")
    )

    assert result["neighbors"] == [
        {
            "peer_ldp_identifier": "192.168.70.6:0",
            "state": "Oper",
            "up_time": "00:02:44",
            "session_holdtime_sec": 180,
            "messages_sent": 851,
            "messages_received": 232,
        }
    ]


def test_second_peer_block_closes_the_first():
    """The fixture has one peer; two copies of it back to back proves a new
    'Peer LDP Identifier' line flushes the block in progress rather than
    merging into it."""
    single = _read_fixture("show_mpls_ldp_neighbor_detail.txt")
    result = parse_mpls_ldp_neighbor_detail(single + single)

    assert len(result["neighbors"]) == 2
    assert result["neighbors"][0] == result["neighbors"][1]
