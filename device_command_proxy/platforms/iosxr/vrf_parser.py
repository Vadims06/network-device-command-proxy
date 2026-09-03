"""Parse `show vrf all detail` (IOS XR) into the neutral VRF schema.

Cross-checked against Genie's iosxr/show_vrf.py oracle
(tests/test_vrf_parser_genie_oracle.py); no Genie code is used here.
"""
from __future__ import annotations

import re

_VRF_HEADER_RE = re.compile(r'^VRF (\S+); RD (\S+|not set);')
_INTERFACES_HEADER_RE = re.compile(r'^Interfaces:\s*$')
_INTERFACE_RE = re.compile(r'^\s+(\S+)\s*$')
_ADDRESS_FAMILY_RE = re.compile(r'^Address family (\S+) (\S+)\s*$')
_ROUTE_TARGET_HEADER_RE = re.compile(r'^\s*(Import|Export) VPN route-target communities:\s*$')
_ROUTE_TARGET_RE = re.compile(r'^\s*RT:(\S+)\s*$')


def _new_vrf(name: str, rd: str) -> dict:
    return {
        "name": name,
        "route_distinguisher": None if rd == "not set" else rd,
        "interfaces": [],
        "families": [],
    }


def parse_vrf_all_detail(output: str) -> dict:
    """Parse the full `show vrf all detail` output into
    {"vrfs": [vrf, ...]} matching schemas.VrfInventory.
    """
    vrfs: list[dict] = []
    vrf: dict | None = None
    in_interfaces = False
    family: dict | None = None
    route_target_direction: str | None = None  # "import" | "export" | None

    for line in output.splitlines():
        if match := _VRF_HEADER_RE.match(line):
            if vrf is not None:
                vrfs.append(vrf)
            vrf = _new_vrf(*match.groups())
            in_interfaces = False
            family = None
            route_target_direction = None
            continue
        if vrf is None:
            continue

        if _INTERFACES_HEADER_RE.match(line):
            in_interfaces = True
            continue
        if in_interfaces:
            if match := _INTERFACE_RE.match(line):
                vrf["interfaces"].append(match.group(1))
                continue
            in_interfaces = False
            # fall through - this line ends the interfaces block

        if match := _ADDRESS_FAMILY_RE.match(line):
            afi, safi = match.groups()
            family = {
                "afi": afi.lower(),
                "safi": safi.lower(),
                "import_route_targets": [],
                "export_route_targets": [],
            }
            vrf["families"].append(family)
            route_target_direction = None
            continue
        if family is None:
            continue

        if match := _ROUTE_TARGET_HEADER_RE.match(line):
            route_target_direction = match.group(1).lower()
            continue
        if route_target_direction and (match := _ROUTE_TARGET_RE.match(line)):
            family[f"{route_target_direction}_route_targets"].append(match.group(1))
            continue
        # "No import/export route policy" and blank lines end the current
        # route-target list without starting a new state.
        route_target_direction = None

    if vrf is not None:
        vrfs.append(vrf)
    return {"vrfs": vrfs}
