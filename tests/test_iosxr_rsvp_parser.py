"""Literal-expectation tests for the IOS XR RSVP session parser, hand-verified
against the copied fixtures - never derived from the parser under test."""
import os

from device_command_proxy.platforms.iosxr.rsvp_parser import parse_rsvp_session_detail

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cisco_iosxr")


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_headend_session_full_fields():
    result = parse_rsvp_session_detail(_read_fixture("show_rsvp_session_detail_headend.txt"))

    assert len(result["sessions"]) == 1
    session = result["sessions"][0]
    assert session["destination"] == "109.109.109.109"
    assert session["tunnel_id"] == "50000"
    assert session["head_end"] == "17.17.17.17"
    assert session["lsp_id"] == "15"
    assert session["tunnel_name"] == "50000_F17-ASR9922_F109-ASR9001"
    assert session["in_label"] == {"interface": "No intf", "label": "No label"}
    assert session["incoming_address"] == "Unknown"
    assert session["explicit_route"] == [
        {"path_status": "strict", "route_address": "20.50.0.1/32"},
        {"path_status": "strict", "route_address": "21.50.0.2/32"},
        {"path_status": "strict", "route_address": "109.109.109.109/32"},
    ]
    assert session["tspec"] == {
        "average_rate": 0.0, "burst": 1.0, "burst_unit": "K", "peak_rate": 0.0,
    }
    assert session["out_label"] == {"interface": "HundredGigE0/0/0/0", "label": "24023"}
    assert session["frr_out_label"] == {"interface": "tunnel-te53300", "label": "3"}
    assert session["fspec"] == {
        "average_rate": 0.0, "burst": 1.0, "burst_unit": "K", "peak_rate": 0.0,
    }


def test_headend_session_record_route_pairs_address_and_label():
    result = parse_rsvp_session_detail(_read_fixture("show_rsvp_session_detail_headend.txt"))
    record_route = result["sessions"][0]["record_route"]

    assert [hop["address"] for hop in record_route] == [
        "141.141.141.141", "20.50.0.1", "109.109.109.109", "21.50.0.2",
    ]
    assert [hop["label_out"] for hop in record_route] == ["24023", "24023", "3", "3"]
    assert [hop["flags_raw"] for hop in record_route] == ["0x21", "0x1", "0x20", "0x0"]


def test_headend_session_record_route_flags_decoded_from_known_bits():
    result = parse_rsvp_session_detail(_read_fixture("show_rsvp_session_detail_headend.txt"))
    flags_by_hop = [hop["flags"] for hop in result["sessions"][0]["record_route"]]

    # 0x21 = bit0 (local_protection_available) + an undecoded higher bit.
    assert flags_by_hop[0] == {
        "local_protection_available": True,
        "local_protection_in_use": False,
        "soft_preempt": False,
        "local_node_protection": False,
    }
    # 0x1 = bit0 (local_protection_available) only.
    assert flags_by_hop[1] == {
        "local_protection_available": True,
        "local_protection_in_use": False,
        "soft_preempt": False,
        "local_node_protection": False,
    }
    # 0x20 = an undecoded higher bit only, no RFC 3209 bits 0-3 set.
    assert flags_by_hop[2] == {
        "local_protection_available": False,
        "local_protection_in_use": False,
        "soft_preempt": False,
        "local_node_protection": False,
    }
    assert flags_by_hop[3] == {
        "local_protection_available": False,
        "local_protection_in_use": False,
        "soft_preempt": False,
        "local_node_protection": False,
    }


def test_headend_session_path_side_record_route_is_dropped():
    """Path Info's "Record Route: None" must never populate record_route -
    only the Resv-side one (with entries) does."""
    result = parse_rsvp_session_detail(_read_fixture("show_rsvp_session_detail_headend.txt"))

    assert len(result["sessions"][0]["record_route"]) == 4  # Resv-side only


def test_egress_multi_session_count_and_identity():
    result = parse_rsvp_session_detail(
        _read_fixture("show_rsvp_session_detail_egress_multi.txt")
    )

    assert len(result["sessions"]) == 5
    assert [s["tunnel_name"] for s in result["sessions"]] == [
        "NHOP_15060_F141-ASR9912_Hu0000_F17-ASR922_Hu0000",
        "NNHOP_16370_F107-ASR9001_F141-ASR9912_F17-ASR9922",
        "NNHOP_16710_F107-ASR9001_F106-ASR9001_F17-ASR9922",
        "55000_F109-ASR9001_F17-ASR9922",
        "56000_F108-ASR9001_F17-ASR9922",
    ]
    assert [s["destination"] for s in result["sessions"]] == ["17.17.17.17"] * 5


def test_egress_session_has_no_reservation():
    """Every session in this fixture is egress on the queried device: no
    OutLabel, no FRR OutLabel, empty Resv-side record route."""
    result = parse_rsvp_session_detail(
        _read_fixture("show_rsvp_session_detail_egress_multi.txt")
    )

    for session in result["sessions"]:
        assert session["out_label"] == {"interface": "No intf", "label": "No label"}
        assert session["frr_out_label"] == {"interface": "No intf", "label": "No label"}
        assert session["record_route"] == []


def test_no_role_field_in_parsed_output():
    """Role is derived by the caller, not the proxy - see schemas.RsvpSession
    docstring and docs/rsvp-parsing.md."""
    result = parse_rsvp_session_detail(
        _read_fixture("show_rsvp_session_detail_egress_multi.txt")
    )

    assert "role" not in result["sessions"][0]
