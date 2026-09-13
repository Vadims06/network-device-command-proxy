"""Parse `show isis interface` (IOS XR) into the neutral IS-IS schema.

Cross-checked against Genie's iosxr/show_isis.py oracle
(tests/test_isis_interface_parser_genie_oracle.py); no Genie code is used here.
Only the summary fields useful for live diagnosis are extracted - the full
per-topology block (FRR, SR labels, BFD, ...) is vendor detail with no
neutral-schema field behind it yet.
"""
from __future__ import annotations

import re

_INTERFACE_HEADER_RE = re.compile(r'^(\S+)\s+(Enabled|Disabled)\s*$')
_CIRCUIT_TYPE_RE = re.compile(r'^\s*Circuit Type:\s*(\S+)')
_MEDIA_TYPE_RE = re.compile(r'^\s*Media Type:\s*(\S+)\s*$')
_LEVEL_HEADER_RE = re.compile(r'^\s*Level-(1|2)\s*$')
_ADJACENCY_COUNT_RE = re.compile(r'^\s*Adjacency Count:\s*(\d+)\s*$')
_METRIC_RE = re.compile(r'^\s*Metric \(L1/L2\):\s*(\d+)/(\d+)\s*$')


def parse_isis_interface(output: str) -> dict:
    """Parse `show isis interface` output into
    {"interfaces": [...]} matching schemas.IsisInterfaces. A device with an
    L1L2 circuit reports adjacency count separately per level, so it is
    tracked per level here too rather than collapsed into one field.
    """
    interfaces: list[dict] = []
    interface: dict | None = None
    current_level: str | None = None
    metric_seen = False

    for line in output.splitlines():
        if match := _INTERFACE_HEADER_RE.match(line):
            if interface is not None:
                interfaces.append(interface)
            interface = {
                "interface": match.group(1),
                "state": match.group(2).lower(),
                "circuit_type": None,
                "media_type": None,
                "adjacency_count_l1": None,
                "adjacency_count_l2": None,
                "metric_l1": None,
                "metric_l2": None,
            }
            current_level = None
            metric_seen = False
            continue
        if interface is None:
            continue

        if match := _CIRCUIT_TYPE_RE.match(line):
            interface["circuit_type"] = match.group(1)
            continue
        if match := _MEDIA_TYPE_RE.match(line):
            interface["media_type"] = match.group(1)
            continue
        if match := _LEVEL_HEADER_RE.match(line):
            current_level = match.group(1)
            continue
        if current_level and (match := _ADJACENCY_COUNT_RE.match(line)):
            interface[f"adjacency_count_l{current_level}"] = int(match.group(1))
            continue
        if not metric_seen and (match := _METRIC_RE.match(line)):
            interface["metric_l1"] = int(match.group(1))
            interface["metric_l2"] = int(match.group(2))
            metric_seen = True
            continue

    if interface is not None:
        interfaces.append(interface)
    return {"interfaces": interfaces}
