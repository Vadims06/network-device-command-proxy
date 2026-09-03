"""Parse `show rsvp session detail` (IOS XR) into the neutral RSVP schema.

Field mapping and the record-route pairing/flag rules are recorded in
docs/rsvp-lsp-schema-freeze.md; this module implements them. No Genie code is
used here - the copied fixtures under tests/fixtures/cisco_iosxr/ are an
independent oracle, exercised by tests/test_rsvp_parser_genie_oracle.py.
"""
from __future__ import annotations

import re

_SESSION_RE = re.compile(r'^SESSION: IPv4-LSP Addr: (\S+), TunID: (\S+), ExtID: (\S+)')
_LSPID_RE = re.compile(r'^\s*LSPId: (\S+)')
_TUNNEL_NAME_RE = re.compile(r'^\s*Tunnel Name: (\S+)')
_LABEL_RE = re.compile(r'^\s*(InLabel|OutLabel|FRR OutLabel): (.+?), (.+)$')
_INCOMING_ADDRESS_RE = re.compile(r'^\s*Incoming Address: (\S+)')
_EXPLICIT_HOP_RE = re.compile(r'^\s*(Strict|Loose), (\S+)$')
_RESERVATION_RE = re.compile(
    r'^\s*[TF]spec: avg rate=(\S+), burst=(\d+)(\D+), peak rate=(\S+)$'
)
_RECORD_ROUTE_ADDRESS_RE = re.compile(r'^\s*IPv4 (\S+), flags (0x[0-9a-fA-F]+)$')
_RECORD_ROUTE_LABEL_RE = re.compile(r'^\s*Label (\S+), flags (0x[0-9a-fA-F]+)$')

# RFC 3209 address-flags bits 0-3; higher bits (e.g. the 0x20 seen in the
# upstream fixture) are IOS XR-specific and not decoded - see the schema
# freeze doc's "open" note. Genie itself does not decode this byte either,
# so there is no oracle for the mapping below, only the bits RFC 3209 defines.
_LOCAL_PROTECTION_AVAILABLE = 0x01
_LOCAL_PROTECTION_IN_USE = 0x02
_SOFT_PREEMPT = 0x04
_LOCAL_NODE_PROTECTION = 0x08


def _decode_flags(flags_hex: str) -> dict:
    value = int(flags_hex, 16)
    return {
        "local_protection_available": bool(value & _LOCAL_PROTECTION_AVAILABLE),
        "local_protection_in_use": bool(value & _LOCAL_PROTECTION_IN_USE),
        "soft_preempt": bool(value & _SOFT_PREEMPT),
        "local_node_protection": bool(value & _LOCAL_NODE_PROTECTION),
    }


def _empty_label() -> dict:
    return {"interface": None, "label": None}


def _new_session(addr: str, tun_id: str, ext_id: str) -> dict:
    return {
        "destination": addr,
        "tunnel_id": tun_id,
        "head_end": ext_id,
        "lsp_id": "",
        "tunnel_name": "",
        "in_label": _empty_label(),
        "incoming_address": None,
        "explicit_route": [],
        "tspec": None,
        "out_label": _empty_label(),
        "frr_out_label": _empty_label(),
        "record_route": [],
        "fspec": None,
    }


def _parse_reservation(match: re.Match) -> dict:
    avg_rate, burst, burst_unit, peak_rate = match.groups()
    return {
        "average_rate": float(avg_rate),
        "burst": float(burst),
        "burst_unit": burst_unit.strip(),
        "peak_rate": float(peak_rate),
    }


def _pair_record_route(entries: list[tuple[str, str, str]]) -> list[dict]:
    """entries: [(kind, value, flags_hex), ...], kind in {"address", "label"}.

    Address entries start a hop; the label entry immediately following an
    address is that hop's outgoing label toward the next hop (see the schema
    freeze doc's pairing rule, verified against golden_output_1).
    """
    hops = []
    pending = None
    for kind, value, flags_hex in entries:
        if kind == "address":
            if pending is not None:
                hops.append(pending)
            pending = {
                "address": value,
                "label_out": None,
                "flags": _decode_flags(flags_hex),
                "flags_raw": flags_hex,
            }
        elif kind == "label" and pending is not None:
            pending["label_out"] = value
    if pending is not None:
        hops.append(pending)
    return hops


def parse_rsvp_session_detail(output: str) -> dict:
    """Parse the full `show rsvp session detail` output into
    {"sessions": [session, ...]} matching schemas.RsvpLspInventory.
    """
    sessions: list[dict] = []
    session: dict | None = None
    in_resv_section = False
    in_resv_record_route = False
    record_route_entries: list[tuple[str, str, str]] = []

    def flush_record_route():
        nonlocal record_route_entries, in_resv_record_route
        if session is not None and in_resv_record_route:
            session["record_route"] = _pair_record_route(record_route_entries)
        record_route_entries = []
        in_resv_record_route = False

    for line in output.splitlines():
        if line.strip() == "RSVP Path Info:":
            in_resv_section = False
            continue
        if line.strip() == "RSVP Resv Info:":
            in_resv_section = True
            continue
        if in_resv_record_route:
            if match := _RECORD_ROUTE_ADDRESS_RE.match(line):
                record_route_entries.append(("address", match.group(1), match.group(2)))
                continue
            if match := _RECORD_ROUTE_LABEL_RE.match(line):
                record_route_entries.append(("label", match.group(1), match.group(2)))
                continue
            # any other line (blank, "Fspec:", "Record Route: None", next
            # section) ends the record-route block; fall through so this
            # same line is still matched against the patterns below
            flush_record_route()

        session_match = _SESSION_RE.match(line)
        if session_match:
            flush_record_route()
            if session is not None:
                sessions.append(session)
            session = _new_session(*session_match.groups())
            continue
        if session is None:
            continue

        if match := _LSPID_RE.match(line):
            session["lsp_id"] = match.group(1)
            continue
        if match := _TUNNEL_NAME_RE.match(line):
            session["tunnel_name"] = match.group(1)
            continue
        if match := _LABEL_RE.match(line):
            field, interface, label = match.groups()
            target = {"InLabel": "in_label", "OutLabel": "out_label", "FRR OutLabel": "frr_out_label"}[field]
            session[target] = {"interface": interface, "label": label}
            continue
        if match := _INCOMING_ADDRESS_RE.match(line):
            session["incoming_address"] = match.group(1)
            continue
        if match := _EXPLICIT_HOP_RE.match(line):
            path_status, route_address = match.groups()
            session["explicit_route"].append(
                {"path_status": path_status.lower(), "route_address": route_address}
            )
            continue
        if match := _RESERVATION_RE.match(line):
            reservation = _parse_reservation(match)
            if "Tspec" in line:
                session["tspec"] = reservation
            else:
                session["fspec"] = reservation
            continue
        if line.strip() == "Record Route:" and in_resv_section:
            # Path-side record route is dropped per the schema freeze, so
            # only a bare "Record Route:" inside RSVP Resv Info starts capture.
            in_resv_record_route = True
            record_route_entries = []
            continue

    flush_record_route()
    if session is not None:
        sessions.append(session)
    return {"sessions": sessions}
