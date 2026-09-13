"""Parse `show bgp neighbors <address>` (IOS XR) into the neutral BGP schema.

Cross-checked against Genie's iosxr/show_bgp.py oracle
(tests/test_bgp_neighbor_detail_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_NEIGHBOR_RE = re.compile(r'^\s*BGP neighbor is (\S+)\s*$')
_AS_RE = re.compile(r'^\s*Remote AS (\d+), local AS (\d+)')
_ROUTER_ID_RE = re.compile(r'^\s*Remote router ID (\S+)\s*$')
_STATE_RE = re.compile(r'^\s*BGP state = (\S+)(?:, up for (\S+))?\s*$')
_HOLD_TIME_RE = re.compile(
    r'^\s*Hold time is (\d+), keepalive interval is (\d+) seconds\s*$'
)
_RECEIVED_RE = re.compile(r'^\s*Received (\d+) messages')
_SENT_RE = re.compile(r'^\s*Sent (\d+) messages')


def parse_bgp_neighbor_detail(output: str) -> dict:
    """Parse `show bgp neighbors <address>` output into
    {"neighbors": [...]} matching schemas.BgpNeighborDetails.
    """
    neighbors: list[dict] = []
    neighbor: dict | None = None

    for line in output.splitlines():
        if match := _NEIGHBOR_RE.match(line):
            if neighbor is not None:
                neighbors.append(neighbor)
            neighbor = {
                "neighbor": match.group(1),
                "remote_as": None,
                "local_as": None,
                "remote_router_id": None,
                "state": None,
                "up_time": None,
                "hold_time_sec": None,
                "keepalive_interval_sec": None,
                "messages_received": None,
                "messages_sent": None,
            }
            continue
        if neighbor is None:
            continue

        if match := _AS_RE.match(line):
            neighbor["remote_as"] = int(match.group(1))
            neighbor["local_as"] = int(match.group(2))
            continue
        if match := _ROUTER_ID_RE.match(line):
            neighbor["remote_router_id"] = match.group(1)
            continue
        if match := _STATE_RE.match(line):
            neighbor["state"] = match.group(1).rstrip(",")
            neighbor["up_time"] = match.group(2)
            continue
        if match := _HOLD_TIME_RE.match(line):
            neighbor["hold_time_sec"] = int(match.group(1))
            neighbor["keepalive_interval_sec"] = int(match.group(2))
            continue
        if match := _RECEIVED_RE.match(line):
            neighbor["messages_received"] = int(match.group(1))
            continue
        if match := _SENT_RE.match(line):
            neighbor["messages_sent"] = int(match.group(1))
            continue

    if neighbor is not None:
        neighbors.append(neighbor)
    return {"neighbors": neighbors}
