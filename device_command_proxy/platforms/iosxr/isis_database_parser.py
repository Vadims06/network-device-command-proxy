"""Parse `show isis database detail` (IOS XR) into the neutral IS-IS schema.

Cross-checked against Genie's iosxr/show_isis.py oracle
(tests/test_isis_database_parser_genie_oracle.py); no Genie code is used here.
Only the per-LSP summary row is extracted - the nested reachability/metric
lines are vendor detail with no neutral-schema field behind it yet.
"""
from __future__ import annotations

import re

_LEVEL_HEADER_RE = re.compile(
    r'^IS-IS (\S+) \((Level-\d)\) Link State Database\s*$'
)
_LSP_ROW_RE = re.compile(
    r'^(\S+?)\s*(\*)?\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(\S+)\s*/\s*(\S+)\s+(\d+/\d+/\d+)\s*$'
)


def parse_isis_database_detail(output: str) -> dict:
    """Parse `show isis database detail` output into
    {"instance": ..., "levels": [{"level": ..., "lsps": [...]}]} matching
    schemas.IsisDatabase. A device dumps one section per IS-IS level it runs.
    """
    instance = None
    levels: list[dict] = []
    current: dict | None = None

    for line in output.splitlines():
        if match := _LEVEL_HEADER_RE.match(line):
            instance, level = match.groups()
            current = {"level": level, "lsps": []}
            levels.append(current)
            continue
        if current is None:
            continue
        if match := _LSP_ROW_RE.match(line):
            lsp_id, own_lsp, seq_num, checksum, holdtime, _received, att_p_ol = (
                match.groups()
            )
            current["lsps"].append(
                {
                    "lsp_id": lsp_id,
                    "own_lsp": own_lsp == "*",
                    "sequence_number": seq_num,
                    "checksum": checksum,
                    "holdtime_sec": None if holdtime == "*" else int(holdtime),
                    "att_p_ol": att_p_ol,
                }
            )

    return {"instance": instance, "levels": levels}
