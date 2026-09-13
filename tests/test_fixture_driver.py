"""A transport=fixture device replays captured text through the real vendor
parser instead of opening SSH; a transport=ssh device is unaffected."""

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError, Transport
from device_command_proxy.fixture_driver import _FixtureSession
from device_command_proxy.platforms.frr.driver import create_adapter as create_frr_adapter
from device_command_proxy.platforms.iosxr.driver import create_adapter as create_iosxr_adapter

_DEMO_PE = DeviceProfile(
    name="123.123.31.31",
    host="123.123.31.31",
    port=22,
    platform="iosxr",
    credential_profile="",
    transport=Transport.FIXTURE,
)


def test_fixture_device_returns_rsvp_lsps_through_the_real_parser():
    adapter = create_iosxr_adapter(_DEMO_PE, credentials=None)

    result = adapter.run("get_rsvp_lsps")

    sessions = result["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["tunnel_id"] == "50000"
    assert sessions[0]["head_end"] == "17.17.17.17"


def test_fixture_device_returns_vrf_detail_through_the_real_parser():
    adapter = create_iosxr_adapter(_DEMO_PE, credentials=None)

    result = adapter.run("get_vrf_detail")

    assert result["vrfs"]


def test_missing_command_fixture_raises_fixture_not_found():
    # 123.123.31.31's map only covers the two IOS XR operations it demos;
    # a command outside that map must fail as fixture_not_found, not KeyError.
    session = _FixtureSession("123.123.31.31")

    try:
        session.send_command("show mpls traffic-eng tunnels")
    except ExecutionError as exception:
        assert exception.code is ErrorCode.FIXTURE_NOT_FOUND
    else:
        raise AssertionError("expected ExecutionError")


def test_missing_device_fixture_map_raises_fixture_not_found():
    device = DeviceProfile(
        name="no-such-demo-device",
        host="192.0.2.1",
        port=22,
        platform="iosxr",
        credential_profile="",
        transport=Transport.FIXTURE,
    )
    adapter = create_iosxr_adapter(device, credentials=None)

    try:
        adapter.run("get_rsvp_lsps")
    except ExecutionError as exception:
        assert exception.code is ErrorCode.FIXTURE_NOT_FOUND
    else:
        raise AssertionError("expected ExecutionError")


def test_ssh_transport_device_does_not_build_a_fixture_driver():
    device = DeviceProfile(
        name="router1",
        host="172.20.20.11",
        port=22,
        platform="frr",
        credential_profile="demo",
        transport=Transport.SSH,
    )

    adapter = create_frr_adapter(device, credentials=None)
    driver = adapter._driver_factory()

    assert not isinstance(driver, _FixtureSession)
