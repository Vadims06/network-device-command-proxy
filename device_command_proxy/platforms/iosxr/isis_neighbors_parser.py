"""Parse `show isis neighbors` (IOS XR) into the neutral IS-IS schema.

Cross-checked against Genie's iosxr/show_isis.py oracle
(tests/test_isis_neighbors_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_INSTANCE_RE = re.compile(r'^IS-IS (\S+) neighbors:\s*$')
_NEIGHBOR_RE = re.compile(
    r'^(\S+)\s+(\S+)\s+(\S+)\s+(Up|Down|Init)\s+(\d+)\s+(\S+)\s+\S+\s*$'
)


def parse_isis_neighbors(output: str) -> dict:
    """Parse `show isis neighbors` output into
    {"instance": ..., "neighbors": [...]} matching schemas.IsisNeighbors.
    """
    instance = None
    neighbors: list[dict] = []

    for line in output.splitlines():
        if match := _INSTANCE_RE.match(line):
            instance = match.group(1)
            continue
        if match := _NEIGHBOR_RE.match(line):
            system_id, interface, snpa, state, holdtime, circuit_type = match.groups()
            neighbors.append(
                {
                    "system_id": system_id,
                    "interface": interface,
                    "snpa": snpa,
                    "state": state.lower(),
                    "holdtime_sec": int(holdtime),
                    "circuit_type": circuit_type.lower(),
                }
            )

    return {"instance": instance, "neighbors": neighbors}
