"""A transport=fixture device replays captured text through the real vendor
parser instead of opening SSH; a transport=ssh device is unaffected."""

import pytest

from device_command_proxy.contracts import DeviceProfile, ErrorCode, ExecutionError, Transport
from device_command_proxy.fixture_driver import _FixtureSession
from device_command_proxy.operation_types import ArgumentKind
from device_command_proxy.operations import OPERATION_SPECS
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


# Literal values read by eye from the captured lab output under
# fixtures/captured/frr/<router>/, not derived from the parser under test.
FRR_DEMO_NEIGHBORS = {
    "123.10.10.10": [
        ("123.123.100.100", "eth1"),
        ("123.123.100.100", "eth2"),
        ("123.123.101.101", "eth3"),
        ("123.11.11.11", "eth4"),
        ("123.30.30.30", "eth5"),
    ],
    "123.30.30.30": [
        ("123.10.10.10", "eth1"),
        ("123.123.30.30", "eth3"),
        ("123.123.31.31", "eth2"),
        ("123.31.31.31", "eth4"),
    ],
    "123.14.14.14": [("123.123.111.111", "eth1"), ("123.123.110.110", "eth2")],
    "123.11.11.11": [
        ("123.10.10.10", "eth1"),
        ("123.123.101.101", "eth2"),
        ("123.123.100.100", "eth3"),
        ("123.31.31.31", "eth4"),
    ],
    "123.13.13.13": [("123.123.101.101", "eth1"), ("123.123.100.100", "eth2")],
    "123.15.15.15": [("123.123.111.111", "eth1"), ("123.123.110.110", "eth2")],
    "123.31.31.31": [
        ("123.11.11.11", "eth1"),
        ("123.30.30.30", "eth2"),
        ("123.123.31.31", "eth3"),
        ("123.123.30.30", "eth4"),
    ],
    "123.123.101.101": [
        ("123.10.10.10", "eth1"),
        ("123.11.11.11", "eth2"),
        ("123.13.13.13", "eth3"),
        ("123.123.100.100", "eth4"),
        ("123.123.110.110", "eth5"),
        ("123.123.111.111", "eth6"),
    ],
    "123.123.110.110": [
        ("123.14.14.14", "eth1"),
        ("123.15.15.15", "eth2"),
        ("123.123.100.100", "eth3"),
        ("123.123.101.101", "eth4"),
        ("123.123.111.111", "eth5"),
    ],
    "123.123.111.111": [
        ("123.14.14.14", "eth1"),
        ("123.15.15.15", "eth2"),
        ("123.123.100.100", "eth3"),
        ("123.123.101.101", "eth4"),
        ("123.123.110.110", "eth5"),
    ],
    "123.123.30.30": [
        ("123.30.30.30", "eth1"),
        ("123.31.31.31", "eth2"),
        ("123.123.31.31", "eth3"),
    ],
}
# The three original devices each route to a direct neighbor; the later
# batch of eight all route to the same far-end hub (123.123.100.100) instead
# of a per-device neighbor pick - one target, still a real multi-hop OSPF
# route, cheaper to keep consistent than to hand-pick eight "interesting" ones.
FRR_DEMO_ROUTES = {
    "123.10.10.10": ("123.30.30.30/32", [("10.1.30.2", "eth5")]),
    "123.30.30.30": ("123.14.14.14/32", [("10.1.30.1", "eth1")]),
    "123.14.14.14": ("123.30.30.30/32", [("10.14.110.2", "eth2"), ("10.14.111.2", "eth1")]),
    "123.11.11.11": ("123.123.100.100/32", [("10.11.100.2", "eth3")]),
    "123.13.13.13": ("123.123.100.100/32", [("10.13.100.2", "eth2")]),
    "123.15.15.15": ("123.123.100.100/32", [("10.15.110.2", "eth2"), ("10.15.111.2", "eth1")]),
    "123.31.31.31": ("123.123.100.100/32", [("10.1.31.1", "eth1")]),
    "123.123.101.101": ("123.123.100.100/32", [("10.100.101.1", "eth4")]),
    "123.123.110.110": ("123.123.100.100/32", [("10.100.110.1", "eth3")]),
    "123.123.111.111": ("123.123.100.100/32", [("10.100.111.1", "eth3")]),
    "123.123.30.30": ("123.123.100.100/32", [("10.30.130.1", "eth1"), ("10.31.130.1", "eth2")]),
}


# (vni, type, vrf, local_vtep, remote_vteps, mac_count) read by eye from the
# 13-hosts-demo-bgp capture; the other FRR demo devices carry no VNI.
FRR_DEMO_EVPN_VNIS = {
    "123.14.14.14": [
        (1010, "l2", "tenant1", "123.14.14.14", ["123.123.30.30", "123.123.31.31", "123.15.15.15"], 1),
        (5000, "l3", "tenant1", "123.14.14.14", None, None),
    ],
    "123.123.30.30": [
        (1010, "l2", "tenant1", "123.123.30.30", ["123.123.31.31", "123.15.15.15", "123.14.14.14"], 1),
        (1020, "l2", "tenant1", "123.123.30.30", ["123.123.31.31"], 0),
        (5000, "l3", "tenant1", "123.123.30.30", None, None),
    ],
    "123.10.10.10": [],
}


def _frr_demo_adapter(device_name):
    return create_frr_adapter(
        DeviceProfile(
            name=device_name,
            host=device_name,
            port=22,
            platform="frr",
            credential_profile="",
            transport=Transport.FIXTURE,
        ),
        credentials=None,
    )


@pytest.mark.parametrize("device_name", FRR_DEMO_NEIGHBORS)
def test_frr_demo_device_lists_its_ospf_neighbors(device_name):
    result = _frr_demo_adapter(device_name).run("get_ospf_neighbors")

    assert [(n["router_id"], n["interface"]) for n in result["neighbors"]] == FRR_DEMO_NEIGHBORS[device_name]
    assert {n["adjacency_state"] for n in result["neighbors"]} == {"full"}


@pytest.mark.parametrize("device_name", FRR_DEMO_ROUTES)
def test_frr_demo_device_resolves_its_route(device_name):
    prefix, next_hops = FRR_DEMO_ROUTES[device_name]

    result = _frr_demo_adapter(device_name).run("get_route", prefix=prefix)

    assert result["matched_prefix"] == prefix
    assert [(h["address"], h["interface"]) for h in result["routes"][0]["next_hops"]] == next_hops


@pytest.mark.parametrize("device_name", FRR_DEMO_ROUTES)
@pytest.mark.parametrize("operation", sorted(_frr_demo_adapter("123.10.10.10")._operation_handlers))
def test_every_frr_operation_is_answered_by_every_frr_demo_device(device_name, operation):
    """A capture missing for one operation would surface as fixture_not_found."""
    spec = OPERATION_SPECS[operation]
    arguments = {
        ArgumentKind.NONE: {},
        ArgumentKind.INTERFACE: {"interface": "eth1"},
        ArgumentKind.PREFIX: {"prefix": FRR_DEMO_ROUTES[device_name][0]},
    }[spec.argument_kind]

    result = _frr_demo_adapter(device_name).run(operation, **arguments)

    assert spec.response_model.model_validate(result)


_DEMO_RR = DeviceProfile(
    name="123.123.100.100",
    host="123.123.100.100",
    port=22,
    platform="iosxr",
    credential_profile="",
    transport=Transport.FIXTURE,
)


def test_demo_route_reflector_bgp_matches_its_topology_identity():
    adapter = create_iosxr_adapter(_DEMO_RR, credentials=None)

    summary = adapter.run("get_bgp_summary")
    detail = adapter.run("get_bgp_neighbor_detail")

    for family in summary["address_families"]:
        assert family["router_id"] == "123.123.100.100"
        assert family["local_as"] == 65000
        assert [peer["neighbor"] for peer in family["neighbors"]] == ["123.123.30.30", "123.123.31.31"]
    assert [peer["neighbor"] for peer in detail["neighbors"]] == ["123.123.30.30", "123.123.31.31"]
    assert [peer["remote_as"] for peer in detail["neighbors"]] == [65000, 65000]


@pytest.mark.parametrize("device_name", FRR_DEMO_EVPN_VNIS)
def test_frr_demo_device_lists_its_evpn_vnis(device_name):
    result = _frr_demo_adapter(device_name).run("get_evpn_vnis")

    assert [(vni["vni"], vni["type"], vni["vrf"], vni["local_vtep"],
             None if vni["remote_vteps"] is None else [vtep["ip"] for vtep in vni["remote_vteps"]],
             vni["mac_count"]) for vni in result["vnis"]] == FRR_DEMO_EVPN_VNIS[device_name]



def test_frr_evpn_vnis_rejects_output_that_is_not_a_vni_list(monkeypatch):
    adapter = _frr_demo_adapter("123.14.14.14")
    monkeypatch.setattr(adapter, "_send_command", lambda command: {"error": "unsupported"})

    with pytest.raises(ExecutionError) as error:
        adapter.run("get_evpn_vnis")

    assert error.value.code == ErrorCode.PARSE_ERROR


def test_frr_evpn_l2_vni_without_peers_has_an_empty_remote_vtep_list(monkeypatch):
    adapter = _frr_demo_adapter("123.14.14.14")
    monkeypatch.setattr(
        adapter, "_send_command",
        lambda command: {"vni": 1020, "type": "L2", "vtepIp": "123.14.14.14", "tenantVrf": "tenant1",
                         "numRemoteVteps": 0, "numMacs": 0},
    )

    vni = adapter.run("get_evpn_vnis")["vnis"][0]

    assert vni["remote_vteps"] == []
    assert vni["mac_count"] == 0
