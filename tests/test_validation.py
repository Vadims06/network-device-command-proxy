import pytest

from execution_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError
from execution_proxy.validation import validate_arguments, validate_devices


DEVICE = DeviceProfile(
    name="router1",
    host="172.20.20.11",
    port=22,
    platform="frr",
    credential_profile="demo-frr-readonly",
    interfaces=frozenset({"eth0", "eth1"}),
)


def test_interface_must_be_in_live_device_inventory():
    with pytest.raises(ExecutionError) as raised_error:
        validate_arguments(
            "get_interface_status",
            {"interface": "eth9"},
            DEVICE,
        )

    assert raised_error.value.code == ErrorCode.INVALID_REQUEST


def test_prefix_is_canonicalized_without_accepting_extra_arguments():
    assert validate_arguments(
        "get_route",
        {"prefix": "10.10.10.6/255.255.255.255"},
        DEVICE,
    ) == {"prefix": "10.10.10.6/32"}


def test_more_than_twenty_devices_is_rejected():
    with pytest.raises(ExecutionError) as raised_error:
        validate_devices(tuple(f"router{number}" for number in range(21)))

    assert raised_error.value.code == ErrorCode.INVALID_REQUEST
