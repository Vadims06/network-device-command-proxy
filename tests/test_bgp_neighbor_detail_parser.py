"""Literal-expectation tests for the IOS XR BGP neighbor detail parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

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


def test_single_neighbor_full_fields():
    result = parse_bgp_neighbor_detail(
        _read_fixture("show_bgp_instance_neighbors_detail.txt")
    )

    assert result["neighbors"] == [
        {
            "neighbor": "10.4.1.1",
            "remote_as": 65000,
            "local_as": 65000,
            "remote_router_id": "10.4.1.1",
            "state": "Established",
            "up_time": "1w1d",
            "hold_time_sec": 180,
            "keepalive_interval_sec": 60,
            "messages_received": 44766,
            "messages_sent": 40667,
        }
    ]


def test_second_neighbor_block_closes_the_first():
    """The fixture has one neighbor; two copies of it back to back proves a
    new 'BGP neighbor is' line flushes the block in progress rather than
    merging into it."""
    single = _read_fixture("show_bgp_instance_neighbors_detail.txt")
    result = parse_bgp_neighbor_detail(single + single)

    assert len(result["neighbors"]) == 2
    assert result["neighbors"][0] == result["neighbors"][1]
