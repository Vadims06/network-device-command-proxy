import httpx
import pytest

from device_command_proxy.contracts import ErrorCode, ExecutionError
from device_command_proxy.netbox_inventory import NetBoxInventoryProvider


def _provider(address="172.21.20.11/24", platform={"slug": "frr"}):
    def handler(request):
        if request.url.path == "/api/dcim/devices/":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 1,
                            "name": "router1",
                            "primary_ip4": (
                                {"address": address} if address is not None else None
                            ),
                            "platform": platform,
                            "custom_fields": {
                                "credential_profile": "demo-frr-readonly",
                                "ssh_port": 22,
                            },
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={"results": [{"name": "eth0"}, {"name": "eth1"}]},
        )

    client = httpx.Client(
        base_url="http://netbox:8080",
        transport=httpx.MockTransport(handler),
    )
    return NetBoxInventoryProvider(
        "http://netbox:8080",
        "nbt_key.secret",
        ["172.21.20.0/24"],
        client=client,
    )


def test_live_device_is_normalized_with_interfaces():
    device = _provider().get_device("router1")

    assert device.name == "router1"
    assert device.host == "172.21.20.11"
    assert device.platform == "frr"
    assert device.credential_profile == "demo-frr-readonly"
    assert device.interfaces == frozenset({"eth0", "eth1"})


def test_address_outside_management_cidr_fails_closed():
    with pytest.raises(ExecutionError) as raised_error:
        _provider("10.0.0.10/24").get_device("router1")

    assert raised_error.value.code == ErrorCode.INVENTORY_UNAVAILABLE
    assert str(raised_error.value) == "live inventory is unavailable or invalid"


def test_null_primary_ip4_is_reported_cleanly_not_as_attribute_error():
    with pytest.raises(ExecutionError) as raised_error:
        _provider(address=None).get_device("router1")

    assert raised_error.value.code == ErrorCode.INVENTORY_UNAVAILABLE
    assert str(raised_error.value) == "live inventory is unavailable or invalid"


def test_zero_results_is_device_not_found_not_inventory_unavailable():
    def handler(request):
        return httpx.Response(200, json={"results": []})

    client = httpx.Client(
        base_url="http://netbox:8080",
        transport=httpx.MockTransport(handler),
    )
    provider = NetBoxInventoryProvider(
        "http://netbox:8080",
        "nbt_key.secret",
        ["172.21.20.0/24"],
        client=client,
    )

    with pytest.raises(ExecutionError) as raised_error:
        provider.get_device("router1")

    assert raised_error.value.code == ErrorCode.DEVICE_NOT_FOUND


def test_netbox_outage_is_reported_as_inventory_unavailable():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(
        base_url="http://netbox:8080",
        transport=httpx.MockTransport(handler),
    )
    provider = NetBoxInventoryProvider(
        "http://netbox:8080",
        "nbt_key.secret",
        ["172.21.20.0/24"],
        client=client,
    )

    with pytest.raises(ExecutionError) as raised_error:
        provider.get_device("router1")

    assert raised_error.value.code == ErrorCode.INVENTORY_UNAVAILABLE
    assert str(raised_error.value) == "live inventory is unavailable or invalid"


def test_null_platform_is_reported_cleanly_not_as_attribute_error():
    device = _provider(platform=None).get_device("router1")

    assert device.platform == ""
