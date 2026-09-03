from device_command_proxy.platforms import PLATFORMS


def test_platforms_registry_has_exactly_frr_junos_and_iosxr():
    assert set(PLATFORMS) == {"frr", "junos", "iosxr"}
    assert all(callable(create_adapter) for create_adapter in PLATFORMS.values())
