"""Literal device output captured per platform, one entry per operation.

Shared by the schema conformance test so every operation is exercised against
real vendor output shapes rather than against hand-built neutral dicts.
"""
import os

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cisco_iosxr")


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def _leaf(value):
    """Wrap a value the way Junos `| display json` wraps every leaf."""
    return [{"data": value}]


FRR_OUTPUT = {
    "get_ospf_neighbors": {
        "ospfInstance": 1,
        "neighbors": {
            "10.10.10.3": [
                {
                    "nbrState": "Full/DR",
                    "role": "DR",
                    "ifaceName": "eth1:192.168.13.1",
                    "ifaceAddress": "192.168.13.3",
                    "routerDeadIntervalTimerDueMsec": 39570,
                }
            ]
        },
    },
    "get_ospf_neighbor_detail": {
        "ospfInstance": 1,
        "neighbors": {
            "10.10.10.3": [
                {
                    "nbrState": "2-Way/DROther",
                    "role": "DROther",
                    "areaId": "0.0.0.0",
                    "ifaceName": "eth1",
                    "ifaceAddress": "192.168.13.3",
                    "routerDeadIntervalTimerDueMsec": 39570,
                    "stateChangeCounter": 4,
                }
            ]
        },
    },
    "get_interface_status": {
        "eth1": {
            "administrativeStatus": "up",
            "operationalStatus": "up",
            "mtu": 9500,
            "speed": 10000,
            "ipAddresses": [{"address": "192.168.13.1/24"}],
        }
    },
    "get_ospf_interface": {
        "interfaces": {
            "eth1": {
                "ifUp": True,
                "ospfEnabled": True,
                "state": "DR",
                "networkType": "BROADCAST",
                "area": "0.0.0.0",
                "cost": 10,
                "timerMsecs": 10000,
                "timerDeadSecs": 40,
                "nbrCount": 2,
                "nbrAdjacentCount": 1,
            }
        }
    },
    "get_ospf_status": {
        "ospfInstance": 1,
        "routerId": "10.10.10.1",
        "areas": {
            "0.0.0.0": {
                "areaIfActiveCounter": 3,
                "nbrFullAdjacentCounter": 2,
                "spfExecutedCounter": 17,
                "lsaNumber": 9,
            }
        },
    },
    "get_route": {
        "10.10.10.0/24": [
            {
                "protocol": "ospf",
                "selected": True,
                "distance": 110,
                "metric": 20,
                "nexthops": [
                    {"ip": "192.168.13.3", "interfaceName": "eth1", "active": True}
                ],
            }
        ]
    },
}
FRR_OUTPUT["get_ospf_interfaces"] = FRR_OUTPUT["get_ospf_interface"]


JUNOS_OUTPUT = {
    "get_ospf_neighbors": {
        "ospf-neighbor-information": [
            {
                "ospf-neighbor": [
                    {
                        "neighbor-id": _leaf("10.10.10.3"),
                        "ospf-neighbor-state": _leaf("Full"),
                        "interface-name": _leaf("ge-0/0/1.0"),
                        "neighbor-address": _leaf("192.168.13.3"),
                        "activity-timer": _leaf("35"),
                    }
                ]
            }
        ]
    },
    "get_ospf_neighbor_detail": {
        "ospf-neighbor-information": [
            {
                "ospf-neighbor": [
                    {
                        "neighbor-id": _leaf("10.10.10.3"),
                        "ospf-neighbor-state": _leaf("2Way"),
                        "ospf-area": _leaf("0.0.0.0"),
                        "interface-name": _leaf("ge-0/0/1.0"),
                        "neighbor-address": _leaf("192.168.13.3"),
                        "activity-timer": _leaf("35"),
                    }
                ]
            }
        ]
    },
    "get_interface_status": {
        "interface-information": [
            {
                "physical-interface": [
                    {
                        "name": _leaf("ge-0/0/1"),
                        "admin-status": _leaf("up"),
                        "oper-status": _leaf("up"),
                        "mtu": _leaf("1500"),
                        "speed": _leaf("1000mbps"),
                        "logical-interface": [
                            {
                                "address-family": [
                                    {
                                        "address-family-name": _leaf("inet"),
                                        "interface-address": [
                                            {"ifa-local": _leaf("192.168.13.1/24")}
                                        ],
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        ]
    },
    "get_ospf_interface": {
        "ospf-interface-information": [
            {
                "ospf-interface": [
                    {
                        "interface-name": _leaf("ge-0/0/1.0"),
                        "ospf-interface-state": _leaf("DR"),
                        "interface-type": _leaf("LAN"),
                        "ospf-area": _leaf("0.0.0.0"),
                        "ospf-interface-cost": _leaf("10"),
                        "hello-interval": _leaf("10"),
                        "dead-interval": _leaf("40"),
                        "neighbor-count": _leaf("2"),
                    }
                ]
            }
        ]
    },
    "get_ospf_status": {
        "ospf-overview-information": [
            {
                "ospf-overview": [
                    {
                        "ospf-router-id": _leaf("10.10.10.1"),
                        "ospf-area-overview": [
                            {
                                "ospf-area": _leaf("0.0.0.0"),
                                "ospf-intf-overview": [
                                    {"ospf-intf-active-count": _leaf("3")}
                                ],
                                "ospf-nbr-overview": [
                                    {"ospf-nbr-up-count": _leaf("2")}
                                ],
                            }
                        ],
                    }
                ]
            }
        ]
    },
    "get_route": {
        "route-information": [
            {
                "route-table": [
                    {
                        "rt": [
                            {
                                "rt-destination": _leaf("10.10.10.0/24"),
                                "rt-entry": [
                                    {
                                        "protocol-name": _leaf("OSPF"),
                                        "current-active": _leaf(None),
                                        "preference": _leaf("10"),
                                        "metric": _leaf("20"),
                                        "nh": [
                                            {
                                                "to": _leaf("192.168.13.3"),
                                                "via": _leaf("ge-0/0/1.0"),
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    },
}
JUNOS_OUTPUT["get_ospf_interfaces"] = JUNOS_OUTPUT["get_ospf_interface"]


# IOS XR is the first text-format platform: the raw `show` output itself, not
# a JSON dict. Reuses the fixture the parser's own tests and the Genie oracle
# read, rather than a second copy of the same capture.
IOSXR_OUTPUT = {
    "get_rsvp_lsps": _read_fixture("show_rsvp_session_detail_headend.txt"),
}


# Arguments each operation needs, matching the fixtures above.
OPERATION_ARGUMENTS = {
    "frr": {
        "get_interface_status": {"interface": "eth1"},
        "get_ospf_interface": {"interface": "eth1"},
        "get_route": {"prefix": "10.10.10.6/32"},
    },
    "junos": {
        "get_interface_status": {"interface": "ge-0/0/1"},
        "get_ospf_interface": {"interface": "ge-0/0/1.0"},
        "get_route": {"prefix": "10.10.10.6/32"},
    },
    "iosxr": {},
}
