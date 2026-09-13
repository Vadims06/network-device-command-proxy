"""Parse `show mpls forwarding` (IOS XR) into the neutral MPLS schema.

Cross-checked against Genie's iosxr/show_mpls.py oracle
(tests/test_mpls_forwarding_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_ENTRY_RE = re.compile(
    r'^(\S+)\s+(\S+)\s+(.+?)\s+(\S+)\s+(\S+)\s+(\d+)\s*$'
)


def parse_mpls_forwarding(output: str) -> dict:
    """Parse `show mpls forwarding` output into
    {"entries": [...]} matching schemas.MplsForwardingTable.
    """
    entries: list[dict] = []

    for line in output.splitlines():
        # The two header rows, the dashes rule, the command echo and the
        # timestamp line all lack a trailing byte count, so the entry
        # pattern already excludes them without a separate word-list guard.
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
