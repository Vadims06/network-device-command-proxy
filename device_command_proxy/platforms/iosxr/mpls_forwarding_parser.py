"""Parse `show mpls forwarding` (IOS XR) into the neutral MPLS schema.

Cross-checked against Genie's iosxr/show_mpls.py oracle
(tests/test_mpls_forwarding_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_ENTRY_RE = re.compile(
    r'^(\S+)\s+(\S+)\s+(.+?)\s+(\S+)\s+(\S+)\s+(\d+)\s*$'
)
_HEADER_WORDS = frozenset({"Local", "Label", "------"})


def parse_mpls_forwarding(output: str) -> dict:
    """Parse `show mpls forwarding` output into
    {"entries": [...]} matching schemas.MplsForwardingTable.
    """
    entries: list[dict] = []

    for line in output.splitlines():
        if not line.strip() or line.split()[0] in _HEADER_WORDS:
            continue
        if match := _ENTRY_RE.match(line):
            local_label, outgoing_label, prefix_or_id, interface, next_hop, byte_count = (
                match.groups()
            )
            entries.append(
                {
                    "local_label": local_label,
                    "outgoing_label": outgoing_label,
                    "prefix_or_id": prefix_or_id,
                    "outgoing_interface": interface,
                    "next_hop": next_hop,
                    "bytes_switched": int(byte_count),
                }
            )

    return {"entries": entries}
