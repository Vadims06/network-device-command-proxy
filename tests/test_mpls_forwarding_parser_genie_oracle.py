"""Cross-check the proxy's own MPLS forwarding parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml).

Genie expands interface abbreviations (`Gi0/0/0/0` -> `GigabitEthernet0/0/0/0`)
that our parser deliberately leaves as the device printed them, so the
cross-check compares next_hop/bytes_switched, not the interface string.
"""
import os

import pytest

genie_show_mpls = pytest.importorskip("genie.libs.parser.iosxr.show_mpls")

import device_command_proxy
from device_command_proxy.platforms.iosxr.mpls_forwarding_parser import parse_mpls_forwarding

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def _genie_entry(genie_result, local_label):
    outgoing_labels = genie_result["local_label"][local_label]["outgoing_label"]
    outgoing_label = next(iter(outgoing_labels))
    prefixes = outgoing_labels[outgoing_label]["prefix_or_id"]
    prefix_or_id = next(iter(prefixes))
    interfaces = prefixes[prefix_or_id]["outgoing_interface"]
    detail = next(iter(interfaces.values()))
    return outgoing_label, prefix_or_id, detail


def test_fixture_agrees_with_genie_on_every_entry():
    output = _read_fixture("show_mpls_forwarding.txt")
    ours = parse_mpls_forwarding(output)
    genie_result = genie_show_mpls.ShowMplsForwarding(device=None).parse(output=output)

    assert set(genie_result["local_label"]) == {e["local_label"] for e in ours["entries"]}
    for entry in ours["entries"]:
        outgoing_label, prefix_or_id, detail = _genie_entry(genie_result, entry["local_label"])
        assert entry["outgoing_label"] == outgoing_label
        assert entry["prefix_or_id"] == prefix_or_id
        assert entry["next_hop"] == detail["next_hop"]
        assert entry["bytes_switched"] == detail["bytes_switched"]
