"""Literal-expectation tests for the IOS XR MPLS forwarding parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

import device_command_proxy
from device_command_proxy.platforms.iosxr.mpls_forwarding_parser import parse_mpls_forwarding

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_entry_count_and_first_three():
    result = parse_mpls_forwarding(_read_fixture("show_mpls_forwarding.txt"))

    assert len(result["entries"]) == 12
    assert result["entries"][:3] == [
        {
            "local_label": "16001",
            "outgoing_label": "Pop",
            "prefix_or_id": "SR Pfx (idx 1)",
            "outgoing_interface": "Gi0/0/0/0",
            "next_hop": "10.1.3.1",
            "bytes_switched": 0,
        },
        {
            "local_label": "16002",
            "outgoing_label": "16002",
            "prefix_or_id": "SR Pfx (idx 2)",
            "outgoing_interface": "Gi0/0/0/0",
            "next_hop": "10.1.3.1",
            "bytes_switched": 0,
        },
        {
            "local_label": "16004",
            "outgoing_label": "Pop",
            "prefix_or_id": "SR Pfx (idx 4)",
            "outgoing_interface": "Gi0/0/0/1",
            "next_hop": "10.3.4.4",
            "bytes_switched": 0,
        },
    ]


def test_pop_and_swap_outgoing_labels_both_parse():
    result = parse_mpls_forwarding(_read_fixture("show_mpls_forwarding.txt"))
    outgoing_labels = {entry["outgoing_label"] for entry in result["entries"]}

    assert "Pop" in outgoing_labels
    assert "16002" in outgoing_labels
