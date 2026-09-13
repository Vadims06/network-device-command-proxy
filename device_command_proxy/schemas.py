"""Public operation result models."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel

from device_command_proxy.operation_types import DataSource, Operation
from device_command_proxy.operation_types import ResultStatus
from device_command_proxy.contracts import ErrorCode


class AdjacencyState(StrEnum):
    DOWN = "down"
    ATTEMPT = "attempt"
    INIT = "init"
    TWO_WAY = "two_way"
    EXSTART = "exstart"
    EXCHANGE = "exchange"
    LOADING = "loading"
    FULL = "full"


class NetworkType(StrEnum):
    BROADCAST_NETWORK = "broadcast_network"
    POINT_TO_POINT_NETWORK = "point_to_point_network"
    NON_BROADCAST_NETWORK = "non_broadcast_network"
    POINT_TO_MULTIPOINT_NETWORK = "point_to_multipoint_network"


class RouterRole(StrEnum):
    DR = "dr"
    BDR = "bdr"
    DR_OTHER = "dr_other"


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


class RsvpLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface: str | None
    label: str | None


class RsvpExplicitRouteHop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_status: Literal["strict", "loose"]
    route_address: str


class RsvpRecordRouteFlags(BaseModel):
    """Record-route address flags: low bits per RFC 3209. Vendor-specific
    higher bits (e.g. the IOS XR 0x20 node-id) are not decoded, only kept in
    the sibling flags_raw. See docs/rsvp-parsing.md."""

    model_config = ConfigDict(extra="forbid")

    local_protection_available: bool
    local_protection_in_use: bool
    soft_preempt: bool
    local_node_protection: bool


class RsvpRecordRouteHop(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str | None
    label_out: str | None
    flags: RsvpRecordRouteFlags | None
    flags_raw: str | None


class RsvpReservation(BaseModel):
    """Tspec (requested) or Fspec (signaled). average_rate's unit is
    unverified: every available fixture reads avg_rate=0."""

    model_config = ConfigDict(extra="forbid")

    average_rate: float
    burst: float
    burst_unit: str
    peak_rate: float


class RsvpSession(BaseModel):
    """One RSVP-TE session as this device sees it. No role field: role
    (ingress/transit/egress) needs the queried device's own router-id, which
    is knowledge the proxy does not have - the caller
    derives it."""

    model_config = ConfigDict(extra="forbid")

    destination: str
    tunnel_id: str
    head_end: str
    lsp_id: str
    tunnel_name: str
    in_label: RsvpLabel
    incoming_address: str | None
    explicit_route: list[RsvpExplicitRouteHop]
    tspec: RsvpReservation
    out_label: RsvpLabel
    frr_out_label: RsvpLabel
    record_route: list[RsvpRecordRouteHop]
    fspec: RsvpReservation


class RsvpLspInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: list[RsvpSession]


class VrfFamily(BaseModel):
    model_config = ConfigDict(extra="forbid")

    afi: str
    safi: str
    import_route_targets: list[str]
    export_route_targets: list[str]


class VrfDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    route_distinguisher: str | None
    interfaces: list[str]
    families: list[VrfFamily]


class VrfInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vrfs: list[VrfDetail]


class BgpNeighborSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neighbor: str
    remote_as: int
    messages_received: int
    messages_sent: int
    up_down: str
    state_or_prefixes_received: str


class BgpAddressFamilySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_family: str
    router_id: str | None
    local_as: int | None
    neighbors: list[BgpNeighborSummary]


class BgpSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_families: list[BgpAddressFamilySummary]


class BgpNeighborDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neighbor: str
    remote_as: int | None
    local_as: int | None
    remote_router_id: str | None
    state: str | None
    up_time: str | None
    hold_time_sec: int | None
    keepalive_interval_sec: int | None
    messages_received: int | None
    messages_sent: int | None


class BgpNeighborDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neighbors: list[BgpNeighborDetail]


class IsisNeighbor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_id: str
    interface: str
    snpa: str
    state: str
    holdtime_sec: int
    circuit_type: str


class IsisNeighbors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance: str | None
    neighbors: list[IsisNeighbor]


class IsisInterfaceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface: str
    state: str
    circuit_type: str | None
    media_type: str | None
    adjacency_count_l1: int | None
    adjacency_count_l2: int | None
    metric_l1: int | None
    metric_l2: int | None


class IsisInterfaces(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interfaces: list[IsisInterfaceState]


class IsisLsp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lsp_id: str
    own_lsp: bool
    sequence_number: str
    checksum: str
    holdtime_sec: int | None
    att_p_ol: str


class IsisLevelDatabase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    lsps: list[IsisLsp]


class IsisDatabase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instance: str | None
    levels: list[IsisLevelDatabase]


class MplsForwardingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_label: str
    outgoing_label: str
    prefix_or_id: str
    outgoing_interface: str
    next_hop: str
    bytes_switched: int


class MplsForwardingTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[MplsForwardingEntry]


class MplsLdpNeighbor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peer_ldp_identifier: str
    state: str | None
    up_time: str | None
    session_holdtime_sec: int | None
    messages_sent: int | None
    messages_received: int | None


class MplsLdpNeighbors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    neighbors: list[MplsLdpNeighbor]


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
    data_source: DataSource


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


class SuccessRsvpLspsResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_RSVP_LSPS]
    status: Literal[ResultStatus.SUCCESS]
    data: RsvpLspInventory
    error: None = None


class SuccessVrfDetailResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_VRF_DETAIL]
    status: Literal[ResultStatus.SUCCESS]
    data: VrfInventory
    error: None = None


class SuccessBgpSummaryResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_BGP_SUMMARY]
    status: Literal[ResultStatus.SUCCESS]
    data: BgpSummary
    error: None = None


class SuccessBgpNeighborDetailResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_BGP_NEIGHBOR_DETAIL]
    status: Literal[ResultStatus.SUCCESS]
    data: BgpNeighborDetails
    error: None = None


class SuccessIsisNeighborsResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_ISIS_NEIGHBORS]
    status: Literal[ResultStatus.SUCCESS]
    data: IsisNeighbors
    error: None = None


class SuccessIsisInterfaceResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_ISIS_INTERFACE]
    status: Literal[ResultStatus.SUCCESS]
    data: IsisInterfaces
    error: None = None


class SuccessIsisDatabaseResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_ISIS_DATABASE]
    status: Literal[ResultStatus.SUCCESS]
    data: IsisDatabase
    error: None = None


class SuccessMplsForwardingResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_MPLS_FORWARDING]
    status: Literal[ResultStatus.SUCCESS]
    data: MplsForwardingTable
    error: None = None


class SuccessLdpNeighborsResultModel(_DeviceResultBase):
    operation: Literal[Operation.GET_LDP_NEIGHBORS]
    status: Literal[ResultStatus.SUCCESS]
    data: MplsLdpNeighbors
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
            SuccessRsvpLspsResultModel,
            SuccessVrfDetailResultModel,
            SuccessBgpSummaryResultModel,
            SuccessBgpNeighborDetailResultModel,
            SuccessIsisNeighborsResultModel,
            SuccessIsisInterfaceResultModel,
            SuccessIsisDatabaseResultModel,
            SuccessMplsForwardingResultModel,
            SuccessLdpNeighborsResultModel,
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
