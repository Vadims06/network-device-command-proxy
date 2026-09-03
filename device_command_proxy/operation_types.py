"""Closed string sets used by the public operation contract."""

from enum import StrEnum


class Operation(StrEnum):
    GET_OSPF_NEIGHBORS = "get_ospf_neighbors"
    GET_OSPF_NEIGHBOR_DETAIL = "get_ospf_neighbor_detail"
    GET_INTERFACE_STATUS = "get_interface_status"
    GET_OSPF_INTERFACE = "get_ospf_interface"
    GET_OSPF_INTERFACES = "get_ospf_interfaces"
    GET_OSPF_STATUS = "get_ospf_status"
    GET_ROUTE = "get_route"
    GET_RSVP_LSPS = "get_rsvp_lsps"
    GET_VRF_DETAIL = "get_vrf_detail"


class ArgumentKind(StrEnum):
    NONE = "none"
    INTERFACE = "interface"
    PREFIX = "prefix"


class AuthenticationType(StrEnum):
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
