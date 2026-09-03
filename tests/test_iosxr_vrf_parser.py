"""Literal-expectation tests for the IOS XR VRF parser, hand-verified
against the copied fixture - never derived from the parser under test."""
import os

from device_command_proxy.platforms.iosxr.vrf_parser import parse_vrf_all_detail

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cisco_iosxr")


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_two_vrfs_parsed():
    result = parse_vrf_all_detail(_read_fixture("show_vrf_all_detail.txt"))

    assert [vrf["name"] for vrf in result["vrfs"]] == ["VRF1", "VRF2"]
    assert [vrf["route_distinguisher"] for vrf in result["vrfs"]] == ["200:1", "200:2"]


def test_vrf1_interfaces():
    result = parse_vrf_all_detail(_read_fixture("show_vrf_all_detail.txt"))
    vrf1 = result["vrfs"][0]

    assert vrf1["interfaces"] == [
        "GigabitEthernet0/0/0/1",
        "GigabitEthernet0/0/0/0.415",
        "GigabitEthernet0/0/0/0.420",
        "GigabitEthernet0/0/0/1.390",
        "GigabitEthernet0/0/0/1.410",
        "GigabitEthernet0/0/0/1.415",
        "GigabitEthernet0/0/0/1.420",
    ]


def test_vrf1_address_families_and_route_targets():
    result = parse_vrf_all_detail(_read_fixture("show_vrf_all_detail.txt"))
    vrf1 = result["vrfs"][0]

    assert [(f["afi"], f["safi"]) for f in vrf1["families"]] == [
        ("ipv4", "unicast"),
        ("ipv6", "unicast"),
    ]
    ipv4 = vrf1["families"][0]
    assert ipv4["import_route_targets"] == ["200:1", "200:2", "300:1", "400:1"]
    assert ipv4["export_route_targets"] == ["200:1"]


def test_vrf2_single_interface_and_symmetric_route_targets():
    result = parse_vrf_all_detail(_read_fixture("show_vrf_all_detail.txt"))
    vrf2 = result["vrfs"][1]

    assert vrf2["interfaces"] == ["GigabitEthernet0/0/0/2"]
    ipv4 = vrf2["families"][0]
    assert ipv4["import_route_targets"] == ["200:2"]
    assert ipv4["export_route_targets"] == ["200:2"]
