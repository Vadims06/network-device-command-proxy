"""Parse `show mpls ldp neighbor detail` (IOS XR) into the neutral MPLS schema.

Cross-checked against Genie's iosxr/show_mpls.py oracle
(tests/test_mpls_ldp_neighbor_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_PEER_RE = re.compile(r'^Peer LDP Identifier:\s*(\S+)\s*$')
_HOLDTIME_RE = re.compile(r'^\s*Session Holdtime:\s*(\d+)\s*sec\s*$')
_STATE_RE = re.compile(
    r'^\s*State:\s*(\S+);\s*Msgs sent/rcvd:\s*(\d+)/(\d+);'
)
_UP_TIME_RE = re.compile(r'^\s*Up time:\s*(\S+)\s*$')


def parse_mpls_ldp_neighbor_detail(output: str) -> dict:
    """Parse `show mpls ldp neighbor detail` output into
    {"neighbors": [...]} matching schemas.MplsLdpNeighbors.
    """
    neighbors: list[dict] = []
    neighbor: dict | None = None

    for line in output.splitlines():
        if match := _PEER_RE.match(line):
            if neighbor is not None:
                neighbors.append(neighbor)
            neighbor = {
                "peer_ldp_identifier": match.group(1),
                "state": None,
                "up_time": None,
                "session_holdtime_sec": None,
                "messages_sent": None,
                "messages_received": None,
            }
            continue
        if neighbor is None:
            continue

        if match := _STATE_RE.match(line):
            neighbor["state"] = match.group(1)
            neighbor["messages_sent"] = int(match.group(2))
            neighbor["messages_received"] = int(match.group(3))
            continue
        if match := _UP_TIME_RE.match(line):
            neighbor["up_time"] = match.group(1)
            continue
        if match := _HOLDTIME_RE.match(line):
            neighbor["session_holdtime_sec"] = int(match.group(1))
            continue

    if neighbor is not None:
        neighbors.append(neighbor)
    return {"neighbors": neighbors}
