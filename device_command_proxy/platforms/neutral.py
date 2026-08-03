"""Vendor-neutral enum values shared by every platform driver.

Field names and enum values follow the OpenConfig OSPFv2 model
(``openconfig-ospf-types``) so a caller can write one rule — "adjacency_state
is not FULL" — that holds on every platform, instead of matching vendor
strings like ``Full/DR`` on one box and ``Full`` on another.

Every mapper returns ``None`` for a value it does not recognise, so an
unmapped vendor string surfaces as a missing enum rather than as a silently
wrong one. The originating string stays available in the matching
``*_raw`` field.
"""

from __future__ import annotations

from typing import Any
from device_command_proxy.schemas import AdjacencyState, NetworkType, RouterRole

_ADJACENCY_STATES = {
    "down": AdjacencyState.DOWN,
    "attempt": AdjacencyState.ATTEMPT,
    "init": AdjacencyState.INIT,
    "2way": AdjacencyState.TWO_WAY,
    "twoway": AdjacencyState.TWO_WAY,
    "exstart": AdjacencyState.EXSTART,
    "exchange": AdjacencyState.EXCHANGE,
    "loading": AdjacencyState.LOADING,
    "full": AdjacencyState.FULL,
}

_NETWORK_TYPES = {
    "broadcast": NetworkType.BROADCAST_NETWORK,
    "lan": NetworkType.BROADCAST_NETWORK,
    "pointopoint": NetworkType.POINT_TO_POINT_NETWORK,
    "pointtopoint": NetworkType.POINT_TO_POINT_NETWORK,
    "p2p": NetworkType.POINT_TO_POINT_NETWORK,
    "nbma": NetworkType.NON_BROADCAST_NETWORK,
    "nonbroadcast": NetworkType.NON_BROADCAST_NETWORK,
    "pointomultipoint": NetworkType.POINT_TO_MULTIPOINT_NETWORK,
    "pointtomultipoint": NetworkType.POINT_TO_MULTIPOINT_NETWORK,
    "p2mp": NetworkType.POINT_TO_MULTIPOINT_NETWORK,
}

_ROUTER_ROLES = {
    "dr": RouterRole.DR,
    "bdr": RouterRole.BDR,
    "backup": RouterRole.BDR,
    "backupdesignatedrouter": RouterRole.BDR,
    "designatedrouter": RouterRole.DR,
    "drother": RouterRole.DR_OTHER,
    "other": RouterRole.DR_OTHER,
}


def _key(value: Any) -> str:
    return "".join(character for character in str(value) if character.isalnum()).lower()


def adjacency_state(raw_state: Any) -> AdjacencyState | None:
    """Map a vendor neighbor state to the OpenConfig adjacency-state enum.

    Vendors append the peer's role to the state (``Full/DR``, ``2-Way/DROther``);
    only the part before the slash is the adjacency state itself.
    """
    if raw_state is None:
        return None
    state = str(raw_state).split("/", 1)[0]
    return _ADJACENCY_STATES.get(_key(state))


def router_role(raw_role: Any) -> RouterRole | None:
    """Map a vendor DR/BDR/DROther designation to the neutral role enum.

    Accepts a bare role and a combined ``<state>/<role>`` string, since some
    platforms only expose the role as a suffix of the neighbor state.
    """
    if raw_role is None:
        return None
    role = str(raw_role)
    if "/" in role:
        role = role.split("/", 1)[1]
    return _ROUTER_ROLES.get(_key(role))


def network_type(raw_network_type: Any) -> NetworkType | None:
    """Map a vendor interface network type to the OpenConfig network-type enum."""
    if raw_network_type is None:
        return None
    return _NETWORK_TYPES.get(_key(raw_network_type))


def raw_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
