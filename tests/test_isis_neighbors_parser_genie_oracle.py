"""Cross-check the proxy's own IS-IS neighbors parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml).

Genie expands interface abbreviations (`Gi0/0/0/0` -> `GigabitEthernet0/0/0/0`)
that our parser deliberately leaves as the device printed them, so the
cross-check keys off system_id instead of the interface string.
"""
import os

import pytest

genie_show_isis = pytest.importorskip("genie.libs.parser.iosxr.show_isis")

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_neighbors_parser import parse_isis_neighbors

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def _genie_neighbors_by_system_id(genie_result, instance):
    vrf = genie_result["isis"][instance]["vrf"]["default"]
    by_system_id = {}
    for interface_data in vrf["interfaces"].values():
        by_system_id.update(interface_data["neighbors"])
    return by_system_id


def test_fixture_agrees_with_genie_on_neighbor_identity_and_state():
    output = _read_fixture("show_isis_neighbors.txt")
    ours = parse_isis_neighbors(output)
    genie_result = genie_show_isis.ShowIsisNeighbors(device=None).parse(output=output)
    genie_neighbors = _genie_neighbors_by_system_id(genie_result, ours["instance"])

    assert {n["system_id"] for n in ours["neighbors"]} == set(genie_neighbors)
    for neighbor in ours["neighbors"]:
        genie_neighbor = genie_neighbors[neighbor["system_id"]]
        assert neighbor["snpa"] == genie_neighbor["snpa"]
        assert neighbor["state"] == genie_neighbor["state"].lower()
        assert neighbor["holdtime_sec"] == int(genie_neighbor["holdtime"])
        assert neighbor["circuit_type"] == genie_neighbor["type"].lower()
