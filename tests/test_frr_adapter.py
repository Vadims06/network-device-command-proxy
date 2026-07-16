import json
from contextlib import nullcontext

import pytest
from scrapli.exceptions import ScrapliConnectionError

from execution_proxy.adapters.frr import FrrAdapter
from execution_proxy.contracts import ErrorCode, ExecutionError


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
    return FrrAdapter(lambda: nullcontext(FakeDriver(command, payload)))


def test_interface_status_normalizes_literal_frr_fixture():
    adapter = _adapter(
        "show interface eth1 json",
        {
            "eth1": {
                "administrativeStatus": "up",
                "operationalStatus": "down",
                "mtu": 9500,
                "speed": 10000,
                "ipAddresses": [
                    {"address": "192.168.13.1/24"},
                    {"address": "fe80::1/64"},
                ],
            }
        },
    )

    assert adapter.run("get_interface_status", interface="eth1") == {
        "interface": "eth1",
        "admin_up": True,
        "oper_up": False,
        "addresses": ["192.168.13.1/24", "fe80::1/64"],
        "mtu": 9500,
        "speed_mbps": 10000,
    }


def test_neighbors_normalize_literal_frr_fixture():
    adapter = _adapter(
        "show ip ospf neighbor json",
        {
            "ospfInstance": 1,
            "neighbors": {
                "10.10.10.3": [
                    {
                        "nbrState": "Full/-",
                        "role": "DROther",
                        "ifaceName": "eth1:192.168.13.1",
                        "ifaceAddress": "192.168.13.3",
                        "routerDeadIntervalTimerDueMsec": 39570,
                    }
                ]
            },
        },
    )

    assert adapter.run("get_ospf_neighbors") == {
        "instance": 1,
        "neighbors": [
            {
                "router_id": "10.10.10.3",
                "state": "Full/-",
                "role": "DROther",
                "interface": "eth1",
                "peer_address": "192.168.13.3",
                "dead_time_ms": 39570,
            }
        ],
    }


def test_route_normalizes_literal_frr_fixture():
    adapter = _adapter(
        "show ip route 10.10.10.6/32 json",
        {
            "10.10.10.6/32": [
                {
                    "protocol": "ospf",
                    "selected": True,
                    "distance": 110,
                    "metric": 20,
                    "nexthops": [
                        {
                            "ip": "192.168.13.3",
                            "interfaceName": "eth1",
                            "active": True,
                        }
                    ],
                }
            ]
        },
    )

    assert adapter.run("get_route", prefix="10.10.10.6/32") == {
        "prefix": "10.10.10.6/32",
        "found": True,
        "routes": [
            {
                "protocol": "ospf",
                "selected": True,
                "distance": 110,
                "metric": 20,
                "next_hops": [
                    {
                        "address": "192.168.13.3",
                        "interface": "eth1",
                        "active": True,
                    }
                ],
            }
        ],
    }


def test_oversized_device_output_is_rejected_before_parsing():
    class OversizedResponse(FakeResponse):
        def __init__(self):
            super().__init__("x" * 1_000_001)

    class OversizedDriver:
        def send_command(self, _command):
            return OversizedResponse()

    adapter = FrrAdapter(lambda: nullcontext(OversizedDriver()))

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("get_ospf_neighbors")

    assert raised_error.value.code == ErrorCode.OUTPUT_TOO_LARGE


def test_free_text_operation_is_rejected_before_driver_creation():
    adapter = FrrAdapter(lambda: pytest.fail("driver must not be created"))

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("run_command", command="configure terminal")

    assert raised_error.value.code == ErrorCode.UNSUPPORTED_OPERATION


def test_transport_failure_is_reported_as_device_unreachable():
    class FailingDriverFactory:
        def __enter__(self):
            raise ScrapliConnectionError("connection refused")

        def __exit__(self, *_exc_info):
            return False

    adapter = FrrAdapter(lambda: FailingDriverFactory())

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run("get_ospf_neighbors")

    assert raised_error.value.code == ErrorCode.DEVICE_UNREACHABLE
