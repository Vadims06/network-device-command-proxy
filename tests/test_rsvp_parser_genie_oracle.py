"""Cross-check the proxy's own parser against Genie's independent parse of
the same fixtures. Requires the optional `genie` dependency group; skipped
otherwise so a normal test run never installs Genie (see pyproject.toml)."""
import os

import pytest

genie_show_rsvp = pytest.importorskip("genie.libs.parser.iosxr.show_rsvp")

from device_command_proxy.platforms.iosxr.rsvp_parser import parse_rsvp_session_detail

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cisco_iosxr")


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def _genie_parse(output):
    return genie_show_rsvp.ShowRSVPSessionDetail(device=None).parse(output=output)


def _genie_sessions(genie_output):
    """Flatten Genie's deeply nested keyed dict into a flat list of session
    field tuples, in the same walk order used to build tunnel_name."""
    sessions = []
    for addr_dd in genie_output["sessions"].values():
        for address, tunid_dd in addr_dd["address"].items():
            for tun_id, extid_dd in tunid_dd["tun_id"].items():
                for ext_id, session_dd in extid_dd["ext_id"].items():
                    for tunnel_name in session_dd["tunnel_name"]:
                        sessions.append((address, tun_id, ext_id, tunnel_name))
    return sessions


def test_headend_fixture_agrees_with_genie_on_identity_fields():
    output = _read_fixture("show_rsvp_session_detail_headend.txt")
    genie_result = _genie_parse(output)
    ours = parse_rsvp_session_detail(output)

    assert _genie_sessions(genie_result) == [
        (s["destination"], s["tunnel_id"], s["head_end"], s["tunnel_name"])
        for s in ours["sessions"]
    ]


def test_egress_multi_fixture_agrees_with_genie_on_identity_fields():
    output = _read_fixture("show_rsvp_session_detail_egress_multi.txt")
    genie_result = _genie_parse(output)
    ours = parse_rsvp_session_detail(output)

    assert _genie_sessions(genie_result) == [
        (s["destination"], s["tunnel_id"], s["head_end"], s["tunnel_name"])
        for s in ours["sessions"]
    ]


def test_headend_fixture_agrees_with_genie_on_record_route_addresses():
    output = _read_fixture("show_rsvp_session_detail_headend.txt")
    genie_result = _genie_parse(output)
    ours = parse_rsvp_session_detail(output)

    genie_record_route = genie_result["sessions"]["IPv4-LSP"]["address"][
        "109.109.109.109"
    ]["tun_id"]["50000"]["ext_id"]["17.17.17.17"]["tunnel_name"][
        "50000_F17-ASR9922_F109-ASR9001"
    ]["rsvp_resv_info"]["record_route"]
    genie_addresses = [
        entry["address"] for entry in genie_record_route.values() if "address" in entry
    ]

    assert genie_addresses == [hop["address"] for hop in ours["sessions"][0]["record_route"]]
