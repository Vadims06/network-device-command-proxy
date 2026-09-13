"""Cross-check the proxy's own IS-IS interface parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_isis = pytest.importorskip("genie.libs.parser.iosxr.show_isis")

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_interface_parser import parse_isis_interface

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_fixture_agrees_with_genie_on_state_and_per_level_adjacency_count():
    output = _read_fixture("show_isis_interface.txt")
    ours = parse_isis_interface(output)
    genie_result = genie_show_isis.ShowIsisInterface(device=None).parse(output=output)

    genie_interfaces = None
    for instance_data in genie_result["instance"].values():
        genie_interfaces = instance_data["interface"]
        break

    assert [iface["interface"] for iface in ours["interfaces"]] == list(genie_interfaces)
    for iface in ours["interfaces"]:
        genie_iface = genie_interfaces[iface["interface"]]
        assert iface["state"] == genie_iface["state"].lower()
        assert iface["circuit_type"] == genie_iface.get("circuit_type")
        assert iface["media_type"] == genie_iface.get("media_type")
        genie_level = genie_iface.get("level", {})
        assert iface["adjacency_count_l1"] == genie_level.get(1, {}).get(
            "adjacency_count"
        )
        assert iface["adjacency_count_l2"] == genie_level.get(2, {}).get(
            "adjacency_count"
        )
