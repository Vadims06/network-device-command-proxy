import pytest

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError
from device_command_proxy.validation import validate_arguments, validate_devices


DEVICE = DeviceProfile(
    name="router1",
    host="172.20.20.11",
    port=22,
    platform="frr",
    credential_profile="demo-frr-readonly",
    interfaces=frozenset({"eth0", "eth1"}),
)


JUNOS_DEVICE = DeviceProfile(
    name="junos1",
    host="172.20.20.12",
    port=22,
    platform="junos",
    credential_profile="demo-junos-readonly",
    interfaces=frozenset({"ge-0/0/0.0", "xe-0/0/1:1"}),
)


@pytest.mark.parametrize("interface", ["ge-0/0/0.0", "xe-0/0/1:1"])
def test_slashed_and_channelized_interface_names_are_accepted(interface):
    assert validate_arguments(
        "get_ospf_interface", {"interface": interface}, JUNOS_DEVICE
    ) == {"interface": interface}


@pytest.mark.parametrize(
    "interface", ["ge-0/0/0.0; reboot", "eth0 | more", "eth0`id`", "eth0$(id)"]
)
def test_shell_metacharacters_are_rejected_even_from_the_inventory(interface):
    device = DeviceProfile(
        name="router1",
        host="172.20.20.11",
        port=22,
        platform="frr",
        credential_profile="demo-frr-readonly",
        interfaces=frozenset({interface}),
    )

    with pytest.raises(ExecutionError) as raised_error:
        validate_arguments("get_ospf_interface", {"interface": interface}, device)

    assert raised_error.value.code == ErrorCode.INVALID_REQUEST


def test_plural_ospf_interfaces_operation_takes_no_arguments():
    assert validate_arguments("get_ospf_interfaces", {}, DEVICE) == {}

    with pytest.raises(ExecutionError):
        validate_arguments("get_ospf_interfaces", {"interface": "eth0"}, DEVICE)


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
