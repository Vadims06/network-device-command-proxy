from device_command_proxy.platforms import PLATFORMS


def test_platforms_registry_has_exactly_frr_and_junos():
    assert set(PLATFORMS) == {"frr", "junos"}
    assert all(callable(create_adapter) for create_adapter in PLATFORMS.values())
