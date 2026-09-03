"""Cross-check the proxy's own VRF parser against Genie's independent parse
of the same fixture. Requires the optional `genie` dependency group; skipped
otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_vrf = pytest.importorskip("genie.libs.parser.iosxr.show_vrf")

from device_command_proxy.platforms.iosxr.vrf_parser import parse_vrf_all_detail

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "cisco_iosxr")


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_vrf_fixture_agrees_with_genie_on_names_and_route_distinguishers():
    output = _read_fixture("show_vrf_all_detail.txt")
    genie_result = genie_show_vrf.ShowVrfAllDetail(device=None).parse(output=output)
    ours = parse_vrf_all_detail(output)

    assert [(name, vrf["route_distinguisher"]) for name, vrf in genie_result.items()] == [
        (vrf["name"], vrf["route_distinguisher"]) for vrf in ours["vrfs"]
    ]


def test_vrf_fixture_agrees_with_genie_on_interfaces():
    output = _read_fixture("show_vrf_all_detail.txt")
    genie_result = genie_show_vrf.ShowVrfAllDetail(device=None).parse(output=output)
    ours = parse_vrf_all_detail(output)

    for our_vrf in ours["vrfs"]:
        assert genie_result[our_vrf["name"]]["interfaces"] == our_vrf["interfaces"]


def test_vrf_fixture_agrees_with_genie_on_route_targets():
    output = _read_fixture("show_vrf_all_detail.txt")
    genie_result = genie_show_vrf.ShowVrfAllDetail(device=None).parse(output=output)
    ours = parse_vrf_all_detail(output)

    for our_vrf in ours["vrfs"]:
        genie_families = genie_result[our_vrf["name"]]["address_family"]
        for family in our_vrf["families"]:
            genie_rts = genie_families[f"{family['afi']} {family['safi']}"]["route_target"]
            genie_import = sorted(
                rt for rt, entry in genie_rts.items() if entry["rt_type"] in ("import", "both")
            )
            genie_export = sorted(
                rt for rt, entry in genie_rts.items() if entry["rt_type"] in ("export", "both")
            )
            assert sorted(family["import_route_targets"]) == genie_import
            assert sorted(family["export_route_targets"]) == genie_export
