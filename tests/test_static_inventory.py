import pytest

from device_command_proxy.contracts import ErrorCode, ExecutionError
from device_command_proxy.static_inventory import StaticInventoryProvider

PLATFORMS = ("frr", "junos")
PROFILES = ("demo-frr-readonly", "demo-junos-readonly")


def _provider(devices, *, supported_platforms=PLATFORMS, credential_profiles=PROFILES):
    return StaticInventoryProvider(
        devices,
        supported_platforms=supported_platforms,
        credential_profiles=credential_profiles,
    )


def _devices(host="172.21.20.11"):
    return {
        "router1": {
            "host": host,
            "port": 22,
            "platform": "frr",
            "credential_profile": "demo-frr-readonly",
            "interfaces": ["eth0", "eth1"],
        }
    }


def test_configured_device_is_returned_with_defaults_applied():
    provider = _provider(_devices())

    device = provider.get_device("router1")

    assert device.name == "router1"
    assert device.host == "172.21.20.11"
    assert device.port == 22
    assert device.platform == "frr"
    assert device.credential_profile == "demo-frr-readonly"
    assert device.interfaces == frozenset({"eth0", "eth1"})


def test_port_defaults_to_22_when_omitted():
    devices = _devices()
    del devices["router1"]["port"]

    device = _provider(devices).get_device("router1")

    assert device.port == 22


def test_unknown_device_is_device_not_found():
    provider = _provider(_devices())

    with pytest.raises(ExecutionError) as raised_error:
        provider.get_device("router2")

    assert raised_error.value.code == ErrorCode.DEVICE_NOT_FOUND


def test_public_management_address_is_supported():
    device = _provider(_devices(host="203.0.113.10")).get_device("router1")

    assert device.host == "203.0.113.10"


def test_missing_required_field_fails_at_startup():
    devices = _devices()
    del devices["router1"]["platform"]

    with pytest.raises(ValueError):
        _provider(devices)


def test_scalar_interfaces_value_fails_at_startup_instead_of_being_split_into_chars():
    devices = _devices()
    devices["router1"]["interfaces"] = "eth0"

    with pytest.raises(ValueError):
        _provider(devices)


def test_misspelled_field_fails_at_startup_instead_of_silently_using_the_default():
    # "interface" (singular) is not a known field: entry.get("interfaces", [])
    # would otherwise silently fall back to [], and every interface-specific
    # request against the device would fail as if the interface were absent.
    devices = _devices()
    devices["router1"]["interface"] = devices["router1"].pop("interfaces")

    with pytest.raises(ValueError, match="unknown field"):
        _provider(devices)


@pytest.mark.parametrize("field", ["platform", "credential_profile"])
@pytest.mark.parametrize("bad_value", [["frr"], {"slug": "frr"}, "", 1])
def test_non_string_or_empty_identifier_fails_at_startup(field, bad_value):
    devices = _devices()
    devices["router1"][field] = bad_value

    with pytest.raises(ValueError):
        _provider(devices)


@pytest.mark.parametrize("bad_port", [0, -1, 65536, 22.5, True, "22"])
def test_invalid_port_fails_at_startup(bad_port):
    devices = _devices()
    devices["router1"]["port"] = bad_port

    with pytest.raises(ValueError):
        _provider(devices)


@pytest.mark.parametrize("bad_host", [2887062539, True, None, ["172", "21", "20", "11"]])
def test_non_string_host_fails_at_startup_instead_of_being_silently_coerced(bad_host):
    devices = _devices()
    devices["router1"]["host"] = bad_host

    with pytest.raises(ValueError):
        _provider(devices)


def test_from_file_loads_json_inventory(tmp_path):
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        '{"router1": {"host": "172.21.20.11", "platform": "frr", '
        '"credential_profile": "demo-frr-readonly", "interfaces": []}}',
        encoding="utf-8",
    )

    device = StaticInventoryProvider.from_file(
        str(inventory_path),
        supported_platforms=PLATFORMS,
        credential_profiles=PROFILES,
    ).get_device("router1")

    assert device.host == "172.21.20.11"


def test_platform_typo_fails_at_startup_not_on_the_first_request():
    devices = _devices()
    devices["router1"]["platform"] = "frrr"

    with pytest.raises(ValueError, match="platform must be one of"):
        _provider(devices)


def test_startup_error_names_the_device_and_the_missing_field():
    devices = _devices()
    del devices["router1"]["credential_profile"]

    with pytest.raises(ValueError, match="router1.*credential_profile"):
        _provider(devices)


def test_at_least_one_supported_platform_is_required():
    with pytest.raises(ValueError):
        _provider(_devices(), supported_platforms=[])


def test_credential_profile_typo_fails_at_startup_not_on_the_first_request():
    devices = _devices()
    devices["router1"]["credential_profile"] = "demo-frr-readonlyy"

    with pytest.raises(ValueError, match="credential_profile must be one of"):
        _provider(devices)


def test_at_least_one_credential_profile_is_required():
    with pytest.raises(ValueError):
        StaticInventoryProvider(
            _devices(),
            supported_platforms=PLATFORMS,
            credential_profiles=[],
        )


@pytest.mark.parametrize("device_name", ["", "r" * 65])
def test_device_name_the_request_path_would_reject_fails_at_startup(device_name):
    # Such an entry would load fine and then be unreachable on every request.
    with pytest.raises(ExecutionError) as raised_error:
        _provider({device_name: _devices()["router1"]})

    assert raised_error.value.code == ErrorCode.INVALID_REQUEST


@pytest.mark.parametrize("interface", ["", "eth0 | more", "eth0; reboot", "eth0`id`"])
def test_interface_name_the_request_path_would_reject_fails_at_startup(interface):
    devices = _devices()
    devices["router1"]["interfaces"] = ["eth0", interface]

    with pytest.raises(ValueError, match="unusable interface names"):
        _provider(devices)


def test_an_ipv4_mapped_host_is_stored_as_plain_ipv4():
    devices = _devices(host="::ffff:172.21.20.11")

    assert _provider(devices).get_device("router1").host == "172.21.20.11"


def test_credential_profile_is_optional_when_nothing_resolves_it():
    # Env credentials cover every device, so requiring the field would be
    # demanding a value no code path reads.
    inventory = StaticInventoryProvider(
        {"router1": {"host": "172.21.20.11", "platform": "frr"}},
        supported_platforms=["frr"],
        credential_profiles=None,
    )

    assert inventory.get_device("router1").credential_profile == ""


def test_credential_profile_is_still_required_when_profiles_are_configured():
    with pytest.raises(ValueError, match="credential_profile"):
        StaticInventoryProvider(
            {"router1": {"host": "172.21.20.11", "platform": "frr"}},
            supported_platforms=["frr"],
            credential_profiles=["demo-frr-readonly"],
        )


def test_a_non_string_credential_profile_is_rejected_even_when_unconstrained():
    with pytest.raises(ValueError, match="credential_profile"):
        StaticInventoryProvider(
            {
                "router1": {
                    "host": "172.21.20.11",
                    "platform": "frr",
                    "credential_profile": 7,
                }
            },
            supported_platforms=["frr"],
            credential_profiles=None,
        )


def test_duplicate_device_key_fails_at_startup_instead_of_silently_merging(tmp_path):
    # json.loads keeps only the last of two duplicate keys, so a copy-paste
    # error could point a familiar device name at the wrong management
    # address without any visible sign in the file's own structure.
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        '{"router1": {"host": "172.21.20.11", "platform": "frr", '
        '"credential_profile": "demo-frr-readonly", "interfaces": []}, '
        '"router1": {"host": "172.21.20.99", "platform": "junos", '
        '"credential_profile": "demo-junos-readonly", "interfaces": []}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate key 'router1'"):
        StaticInventoryProvider.from_file(
            str(inventory_path),
            supported_platforms=PLATFORMS,
            credential_profiles=PROFILES,
        )
