"""Parse `show bgp instance summary` (IOS XR) into the neutral BGP schema.

Cross-checked against Genie's iosxr/show_bgp.py oracle
(tests/test_bgp_summary_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_ADDRESS_FAMILY_RE = re.compile(r'^\s*Address Family:\s*(.+?)\s*$')
_ROUTER_ID_RE = re.compile(
    r'^\s*BGP router identifier (\S+), local AS number (\d+)\s*$'
)
_NEIGHBOR_RE = re.compile(
    r'^\s*(\S+)\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+\s+(\S+)\s+(\S+)\s*$'
)


def parse_bgp_instance_summary(output: str) -> dict:
    """Parse the full `show bgp instance summary` output into
    {"address_families": [...]} matching schemas.BgpSummary.
    """
    address_families: list[dict] = []
    family: dict | None = None

    for line in output.splitlines():
        if match := _ADDRESS_FAMILY_RE.match(line):
            family = {
                "address_family": match.group(1).lower(),
                "router_id": None,
                "local_as": None,
                "neighbors": [],
            }
            address_families.append(family)
            continue
        if family is None:
            continue

        if match := _ROUTER_ID_RE.match(line):
            family["router_id"] = match.group(1)
            family["local_as"] = int(match.group(2))
            continue

        if match := _NEIGHBOR_RE.match(line):
            neighbor, msg_rcvd, msg_sent, remote_as, up_down, state_or_pfxrcd = (
                match.group(1),
                match.group(3),
                match.group(4),
                match.group(2),
                match.group(5),
                match.group(6),
            )
            family["neighbors"].append(
                {
                    "neighbor": neighbor,
                    "remote_as": int(remote_as),
                    "messages_received": int(msg_rcvd),
                    "messages_sent": int(msg_sent),
                    "up_down": up_down,
                    "state_or_prefixes_received": state_or_pfxrcd,
                }
            )

    return {"address_families": address_families}
