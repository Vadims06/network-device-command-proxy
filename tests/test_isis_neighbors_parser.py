"""Literal-expectation tests for the IOS XR IS-IS neighbors parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_neighbors_parser import parse_isis_neighbors

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_instance_and_neighbors():
    result = parse_isis_neighbors(_read_fixture("show_isis_neighbors.txt"))

    assert result["instance"] == "test"
    assert result["neighbors"] == [
        {
            "system_id": "R1_xe",
            "interface": "Gi0/0/0/0.115",
            "snpa": "fa16.3eff.4f49",
            "state": "up",
            "holdtime_sec": 24,
            "circuit_type": "l1l2",
        },
        {
            "system_id": "R3_nx",
            "interface": "Gi0/0/0/1.115",
            "snpa": "5e00.40ff.0209",
            "state": "up",
            "holdtime_sec": 25,
            "circuit_type": "l1l2",
        },
    ]
