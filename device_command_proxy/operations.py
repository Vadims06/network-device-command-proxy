"""The single registry of supported semantic operations."""

from __future__ import annotations

from dataclasses import dataclass
from pydantic import BaseModel

from device_command_proxy.schemas import (
    InterfaceStatus,
    OspfInterfaces,
    OspfNeighborDetails,
    OspfNeighbors,
    OspfStatus,
    RouteLookup,
)
from device_command_proxy.operation_types import ArgumentKind, Operation


@dataclass(frozen=True)
class OperationSpec:
    operation: Operation
    argument_kind: ArgumentKind
    response_model: type[BaseModel]


OPERATION_SPECS = {
    Operation.GET_OSPF_NEIGHBORS: OperationSpec(
        Operation.GET_OSPF_NEIGHBORS, ArgumentKind.NONE, OspfNeighbors
    ),
    Operation.GET_OSPF_NEIGHBOR_DETAIL: OperationSpec(
        Operation.GET_OSPF_NEIGHBOR_DETAIL, ArgumentKind.NONE, OspfNeighborDetails
    ),
    Operation.GET_INTERFACE_STATUS: OperationSpec(
        Operation.GET_INTERFACE_STATUS, ArgumentKind.INTERFACE, InterfaceStatus
    ),
    Operation.GET_OSPF_INTERFACE: OperationSpec(
        Operation.GET_OSPF_INTERFACE, ArgumentKind.INTERFACE, OspfInterfaces
    ),
    Operation.GET_OSPF_INTERFACES: OperationSpec(
        Operation.GET_OSPF_INTERFACES, ArgumentKind.NONE, OspfInterfaces
    ),
    Operation.GET_OSPF_STATUS: OperationSpec(
        Operation.GET_OSPF_STATUS, ArgumentKind.NONE, OspfStatus
    ),
    Operation.GET_ROUTE: OperationSpec(
        Operation.GET_ROUTE, ArgumentKind.PREFIX, RouteLookup
    ),
}


ALLOWED_OPERATIONS = frozenset(OPERATION_SPECS)


def operation_spec(operation: str) -> OperationSpec:
    try:
        return OPERATION_SPECS[Operation(operation)]
    except (KeyError, ValueError) as exception:
        raise ValueError(f"unsupported operation: {operation}") from exception
