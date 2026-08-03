import json
from contextlib import nullcontext

import pytest
from scrapli.exceptions import ScrapliConnectionError

from device_command_proxy.contracts import DeviceCredentials, DeviceProfile, ErrorCode, ExecutionError
from device_command_proxy.platforms.frr import driver as frr_driver
from device_command_proxy.platforms.frr.driver import FrrAdapter


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
                "adjacency_state": "FULL",
                "state_raw": "Full/-",
                "role": "DR_OTHER",
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
        "matched_prefix": "10.10.10.6/32",
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


def test_create_frr_driver_ensures_host_key_before_opening(monkeypatch):
    call_order = []

    def fake_ensure_host_key(host, port, known_hosts_file):
        assert (host, port, known_hosts_file) == ("10.0.0.9", 22, "/tmp/known_hosts")
        call_order.append("ensure_host_key")

    class FakeGenericDriver:
        def __init__(self, **_kwargs):
            pass

        def open(self):
            call_order.append("open")

        def isalive(self):
            return False

    monkeypatch.setattr(frr_driver, "ensure_host_key", fake_ensure_host_key)
    monkeypatch.setattr(frr_driver, "GenericDriver", FakeGenericDriver)

    device = DeviceProfile(
        name="r1",
        host="10.0.0.9",
        port=22,
        platform="frr",
        credential_profile="default",
    )
    credentials = DeviceCredentials(
        username="diag", authentication_type="password", password="secret"
    )

    with frr_driver.create_frr_driver(
        device, credentials, known_hosts_file="/tmp/known_hosts"
    ):
        pass

    assert call_order == ["ensure_host_key", "open"]


def test_role_is_derived_from_the_state_suffix_when_frr_omits_the_role_key():
    # Releases without a separate `role` key still carry it in nbrState.
    adapter = _adapter(
        "show ip ospf neighbor json",
        {
            "ospfInstance": 1,
            "neighbors": {
                "10.10.10.3": [
                    {
                        "nbrState": "2-Way/DROther",
                        "ifaceName": "eth1:192.168.13.1",
                        "ifaceAddress": "192.168.13.3",
                        "routerDeadIntervalTimerDueMsec": 39570,
                    }
                ]
            },
        },
    )

    neighbor = adapter.run("get_ospf_neighbors")["neighbors"][0]

    assert neighbor["adjacency_state"] == "TWO_WAY"
    assert neighbor["role"] == "DR_OTHER"


def test_point_to_point_state_suffix_yields_no_role():
    adapter = _adapter(
        "show ip ospf neighbor json",
        {
            "ospfInstance": 1,
            "neighbors": {
                "10.10.10.3": [
                    {
                        "nbrState": "Full/-",
                        "ifaceName": "eth1",
                        "ifaceAddress": "192.168.13.3",
                        "routerDeadIntervalTimerDueMsec": 39570,
                    }
                ]
            },
        },
    )

    assert adapter.run("get_ospf_neighbors")["neighbors"][0]["role"] is None
