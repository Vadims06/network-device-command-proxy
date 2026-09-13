"""Literal-expectation tests for the IOS XR IS-IS interface parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_interface_parser import parse_isis_interface

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_interface_names_and_states():
    result = parse_isis_interface(_read_fixture("show_isis_interface.txt"))

    assert [iface["interface"] for iface in result["interfaces"]] == [
        "Loopback0",
        "GigabitEthernet0/0/0/0",
        "GigabitEthernet0/0/0/1",
        "GigabitEthernet0/0/0/2",
        "GigabitEthernet0/0/0/3",
        "tunnel-te105",
    ]
    assert {iface["state"] for iface in result["interfaces"]} == {"enabled"}


def test_gigabitethernet0_full_fields():
    """Level-1 and Level-2 adjacency counts differ on this interface (0 vs 1
    in the fixture) - a single collapsed field would silently pick one."""
    result = parse_isis_interface(_read_fixture("show_isis_interface.txt"))
    iface = result["interfaces"][1]

    assert iface == {
        "interface": "GigabitEthernet0/0/0/0",
        "state": "enabled",
        "circuit_type": "level-1-2",
        "media_type": "LAN",
        "adjacency_count_l1": 0,
        "adjacency_count_l2": 1,
        "metric_l1": 10,
        "metric_l2": 10,
    }


def test_tunnel_interface_circuit_type_ignores_trailing_annotation():
    """The device appends '(Interface circuit type is level-1-2)' to this
    line for a TE tunnel; only the leading value is the field. The tunnel
    also has no Level-1/Level-2 adjacency block, so those stay null rather
    than a fabricated value."""
    result = parse_isis_interface(_read_fixture("show_isis_interface.txt"))
    tunnel = result["interfaces"][-1]

    assert tunnel["interface"] == "tunnel-te105"
    assert tunnel["circuit_type"] == "level-2-only"
    assert tunnel["adjacency_count_l1"] is None
    assert tunnel["adjacency_count_l2"] is None
