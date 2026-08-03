import json
from contextlib import nullcontext

import pytest
from scrapli.exceptions import ScrapliConnectionError

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile, ErrorCode, ExecutionError
from device_command_proxy.platforms.junos import driver as junos_driver
from device_command_proxy.platforms.junos.driver import JunosAdapter


class FakeResponse:
    def __init__(self, result, *, failed=False):
        self.result = result
        self.failed = failed


class FakeDriver:
    def __init__(self, expected_command, payload):
        self.expected_command = expected_command
        self.payload = payload

    def send_command(self, command):
        assert command == self.expected_command
        return FakeResponse(json.dumps(self.payload))


def _adapter(command, payload):
    return JunosAdapter(lambda: nullcontext(FakeDriver(command, payload)))


def _leaf(value):
    return [{"data": value}]


def test_interface_status_normalizes_literal_junos_fixture():
    adapter = _adapter(
        "show interfaces ge-0/0/1 | display json",
        {
            "interface-information": [
                {
                    "physical-interface": [
                        {
                            "name": _leaf("ge-0/0/1"),
                            "admin-status": _leaf("up"),
                            "oper-status": _leaf("down"),
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
    )

    assert adapter.run("get_interface_status", interface="ge-0/0/1") == {
        "interface": "ge-0/0/1",
        "admin_up": True,
        "oper_up": False,
        "addresses": ["192.168.13.1/24"],
        "mtu": 1500,
        "speed_mbps": 1000,
    }


def test_neighbors_normalize_literal_junos_fixture():
    adapter = _adapter(
        "show ospf neighbor | display json",
        {
            "ospf-neighbor-information": [
                {
                    "ospf-neighbor": [
                        {
                            "neighbor-address": _leaf("192.168.13.3"),
                            "interface-name": _leaf("ge-0/0/1.0"),
                            "ospf-neighbor-state": _leaf("Full"),
                            "neighbor-id": _leaf("10.10.10.3"),
                            "activity-timer": _leaf("39"),
                        }
                    ]
                }
            ]
        },
    )

    assert adapter.run("get_ospf_neighbors") == {
        "instance": None,
        "neighbors": [
            {
                "router_id": "10.10.10.3",
                "adjacency_state": "full",
                "state_raw": "full",
                "role": None,
                "interface": "ge-0/0/1.0",
                "peer_address": "192.168.13.3",
                "dead_time_ms": 39000,
            }
        ],
    }


def test_route_normalizes_literal_junos_fixture():
    adapter = _adapter(
        "show route 10.10.10.6/32 | display json",
        {
            "route-information": [
                {
                    "route-table": [
                        {
                            "rt": [
                                {
                                    "rt-destination": _leaf("10.10.10.6/32"),
                                    "rt-entry": [
                                        {
                                            "protocol-name": _leaf("OSPF"),
                                            "preference": _leaf("10"),
                                            "metric": _leaf("20"),
                                            "current-active": _leaf(""),
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
    )

    assert adapter.run("get_route", prefix="10.10.10.6/32") == {
        "prefix": "10.10.10.6/32",
        "matched_prefix": "10.10.10.6/32",
        "found": True,
        "routes": [
            {
                "protocol": "ospf",
                "selected": True,
                "distance": 10,
                "metric": 20,
                "next_hops": [
                    {
                        "address": "192.168.13.3",
                        "interface": "ge-0/0/1.0",
                        "active": True,
                    }
                ],
            }
        ],
    }


def test_ospf_status_normalizes_literal_junos_fixture():
    adapter = _adapter(
        "show ospf overview | display json",
        {
            "ospf-overview-information": [
                {
                    "ospf-overview": [
                        {
                            "ospf-router-id": _leaf("10.10.10.2"),
                            "ospf-area-overview": [
                                {
                                    "ospf-area": _leaf("0.0.0.0"),
                                    "ospf-nbr-overview": [
                                        {"ospf-nbr-up-count": _leaf("1")}
                                    ],
                                    "ospf-intf-overview": [
                                        {"ospf-intf-active-count": _leaf("2")}
                                    ],
                                }
                            ],
                        }
                    ]
                }
            ]
        },
    )

    assert adapter.run("get_ospf_status") == {
        "instance": None,
        "router_id": "10.10.10.2",
        "areas": [
            {
                "area": "0.0.0.0",
                "active_interfaces": 2,
                "full_neighbors": 1,
                "spf_runs": None,
                "lsa_count": None,
            }
        ],
    }


def test_ospf_interface_normalizes_literal_junos_fixture():
    adapter = _adapter(
        "show ospf interface ge-0/0/1.0 detail | display json",
        {
            "ospf-interface-information": [
                {
                    "ospf-interface": [
                        {
                            "interface-name": _leaf("ge-0/0/1.0"),
                            "ospf-area": _leaf("0.0.0.0"),
                            "interface-type": _leaf("P2P"),
                            "ospf-interface-state": _leaf("PtToPt"),
                            "neighbor-count": _leaf("1"),
                            "ospf-interface-cost": _leaf("100"),
                            "hello-interval": _leaf("10"),
                            "dead-interval": _leaf("40"),
                        }
                    ]
                }
            ]
        },
    )

    assert adapter.run("get_ospf_interface", interface="ge-0/0/1.0") == {
        "interfaces": [
            {
                "interface": "ge-0/0/1.0",
                "up": True,
                "enabled": True,
                "state": "PtToPt",
                "network_type": "point_to_point_network",
                "network_type_raw": "p2p",
                "area": "0.0.0.0",
                "cost": 100,
                "hello_interval_ms": 10000,
                "dead_interval_sec": 40,
                "neighbors": 1,
                "adjacent_neighbors": None,
            }
        ]
    }


def test_free_text_operation_is_rejected_before_driver_creation():
    adapter = JunosAdapter(lambda: pytest.fail("driver must not be created"))

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("run_command", command="configure")

    assert raised_error.value.code == ErrorCode.UNSUPPORTED_OPERATION


def test_oversized_device_output_is_rejected_before_parsing():
    class OversizedDriver:
        def send_command(self, _command):
            return FakeResponse("x" * 1_000_001)

    adapter = JunosAdapter(lambda: nullcontext(OversizedDriver()))

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("get_ospf_neighbors")

    assert raised_error.value.code == ErrorCode.OUTPUT_TOO_LARGE


def test_transport_failure_is_reported_as_device_unreachable():
    class FailingDriverFactory:
        def __enter__(self):
            raise ScrapliConnectionError("connection refused")

        def __exit__(self, *_exc_info):
            return False

    adapter = JunosAdapter(lambda: FailingDriverFactory())

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("get_ospf_neighbors")

    assert raised_error.value.code == ErrorCode.DEVICE_UNREACHABLE


def test_create_junos_driver_ensures_host_key_before_opening(monkeypatch):
    call_order = []

    def fake_ensure_host_key(host, port, known_hosts_file):
        assert (host, port, known_hosts_file) == ("10.0.0.9", 22, "/tmp/known_hosts")
        call_order.append("ensure_host_key")

    class FakeJunosDriver:
        def __init__(self, **_kwargs):
            pass

        def open(self):
            call_order.append("open")

        def isalive(self):
            return False

    monkeypatch.setattr(junos_driver, "ensure_host_key", fake_ensure_host_key)
    monkeypatch.setattr(junos_driver, "JunosDriver", FakeJunosDriver)

    device = DeviceProfile(
        name="r1",
        host="10.0.0.9",
        port=22,
        platform="junos",
        credential_profile="default",
    )
    credentials = DeviceCredentials(
        username="diag", authentication_type="password", password="secret"
    )

    with junos_driver.create_junos_driver(
        device, credentials, known_hosts_file="/tmp/known_hosts"
    ):
        pass

    assert call_order == ["ensure_host_key", "open"]
