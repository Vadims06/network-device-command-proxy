"""Public operation result models."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel

from device_command_proxy.operation_types import Operation
from device_command_proxy.operation_types import ResultStatus
from device_command_proxy.contracts import ErrorCode


class AdjacencyState(StrEnum):
    DOWN = "DOWN"
    ATTEMPT = "ATTEMPT"
    INIT = "INIT"
    TWO_WAY = "TWO_WAY"
    EXSTART = "EXSTART"
    EXCHANGE = "EXCHANGE"
    LOADING = "LOADING"
    FULL = "FULL"


class NetworkType(StrEnum):
    BROADCAST_NETWORK = "BROADCAST_NETWORK"
    POINT_TO_POINT_NETWORK = "POINT_TO_POINT_NETWORK"
    NON_BROADCAST_NETWORK = "NON_BROADCAST_NETWORK"
    POINT_TO_MULTIPOINT_NETWORK = "POINT_TO_MULTIPOINT_NETWORK"


class RouterRole(StrEnum):
    DR = "DR"
    BDR = "BDR"
    DR_OTHER = "DR_OTHER"


class InterfaceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface: str
    admin_up: bool | None
    oper_up: bool | None
    addresses: list[str]
    mtu: int | None
    speed_mbps: int | None


class OspfNeighbor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    router_id: str | None
    adjacency_state: AdjacencyState | None
    state_raw: str | None
    role: RouterRole | None
    interface: str | None
    peer_address: str | None
    dead_time_ms: int | None


class OspfNeighborDetail(OspfNeighbor):
    area: str | None
    state_changes: int | None


class OspfNeighbors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance: int | None
    neighbors: list[OspfNeighbor]


class OspfNeighborDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance: int | None
    neighbors: list[OspfNeighborDetail]


class OspfInterface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface: str | None
    up: bool | None
    enabled: bool | None
    state: str | None
    network_type: NetworkType | None
    network_type_raw: str | None
    area: str | None
    cost: int | None
    hello_interval_ms: int | None
    dead_interval_sec: int | None
    neighbors: int | None
    adjacent_neighbors: int | None


class OspfInterfaces(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interfaces: list[OspfInterface]


class OspfArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str | None
    active_interfaces: int | None
    full_neighbors: int | None
    spf_runs: int | None
    lsa_count: int | None


class OspfStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance: int | None
    router_id: str | None
    areas: list[OspfArea]


class RouteNextHop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str | None
    interface: str | None
    active: bool


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol: str | None
    selected: bool
    distance: int | None
    metric: int | None
    next_hops: list[RouteNextHop]


class RouteLookup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefix: str
    matched_prefix: str | None
    found: bool
    routes: list[Route]


class OperationErrorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str


class BadRequestResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: OperationErrorModel


class UnauthorizedResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str


class _DeviceResultBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: str
    platform: str
    duration_ms: int
    unsupported_fields: list[str]


class DeviceErrorResultModel(_DeviceResultBase):
    operation: Operation
    status: Literal[ResultStatus.ERROR]
    data: None = Field(...)
    error: OperationErrorModel


class SuccessOspfNeighborsResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_OSPF_NEIGHBORS]
    status: Literal[ResultStatus.SUCCESS]
    data: OspfNeighbors
    error: None = None


class SuccessOspfNeighborDetailsResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_OSPF_NEIGHBOR_DETAIL]
    status: Literal[ResultStatus.SUCCESS]
    data: OspfNeighborDetails
    error: None = None


class SuccessInterfaceStatusResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_INTERFACE_STATUS]
    status: Literal[ResultStatus.SUCCESS]
    data: InterfaceStatus
    error: None = None


class SuccessOspfInterfacesResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_OSPF_INTERFACES]
    status: Literal[ResultStatus.SUCCESS]
    data: OspfInterfaces
    error: None = None


class SuccessOspfInterfaceResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_OSPF_INTERFACE]
    status: Literal[ResultStatus.SUCCESS]
    data: OspfInterfaces
    error: None = None


class SuccessOspfStatusResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_OSPF_STATUS]
    status: Literal[ResultStatus.SUCCESS]
    data: OspfStatus
    error: None = None


class SuccessRouteResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_ROUTE]
    status: Literal[ResultStatus.SUCCESS]
    data: RouteLookup
    error: None = None


DeviceSuccessResultModel = RootModel[
    Annotated[
        Union[
            SuccessOspfNeighborsResultModel,
            SuccessOspfNeighborDetailsResultModel,
            SuccessInterfaceStatusResultModel,
            SuccessOspfInterfacesResultModel,
            SuccessOspfInterfaceResultModel,
            SuccessOspfStatusResultModel,
            SuccessRouteResultModel,
        ],
        Field(discriminator="operation"),
    ]
]


class DeviceResultModel(
    RootModel[
        Annotated[
            Union[DeviceSuccessResultModel, DeviceErrorResultModel],
            Field(discriminator="status"),
        ]
    ]
):
    pass


class ExecuteResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    results: list[DeviceResultModel]
