"""Literal-expectation tests for the IOS XR BGP summary parser, hand-verified
against the copied fixture - never derived from the parser under test."""
import os

import device_command_proxy
from device_command_proxy.platforms.iosxr.bgp_summary_parser import parse_bgp_instance_summary

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_address_families_and_router_id():
    result = parse_bgp_instance_summary(_read_fixture("show_bgp_instance_summary.txt"))

    assert [af["address_family"] for af in result["address_families"]] == [
        "vpnv4 unicast",
        "vpnv6 unicast",
    ]
    for af in result["address_families"]:
        assert af["router_id"] == "10.4.1.1"
        assert af["local_as"] == 100


def test_neighbors_of_first_address_family():
    result = parse_bgp_instance_summary(_read_fixture("show_bgp_instance_summary.txt"))
    neighbors = result["address_families"][0]["neighbors"]

    assert neighbors == [
        {
            "neighbor": "10.16.2.2",
            "remote_as": 100,
            "messages_received": 59,
            "messages_sent": 56,
            "up_down": "00:50:38",
            "state_or_prefixes_received": "10",
        },
        {
            "neighbor": "10.36.3.3",
            "remote_as": 100,
            "messages_received": 68,
            "messages_sent": 58,
            "up_down": "00:47:11",
            "state_or_prefixes_received": "10",
        },
    ]
