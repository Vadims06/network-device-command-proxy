"""Cross-check the proxy's own IS-IS database parser against Genie's
independent parse of the same fixture. Requires the optional `genie`
dependency group; skipped otherwise (see pyproject.toml)."""
import os

import pytest

genie_show_isis = pytest.importorskip("genie.libs.parser.iosxr.show_isis")

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_database_parser import (
    parse_isis_database_detail,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)

_LEVEL_NUMBER = {"Level-1": 1, "Level-2": 2}


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_fixture_agrees_with_genie_on_lsp_identity_and_holdtime():
    output = _read_fixture("show_isis_database_detail.txt")
    ours = parse_isis_database_detail(output)
    genie_result = genie_show_isis.ShowIsisDatabaseDetail(device=None).parse(output=output)

    genie_levels = genie_result["instance"][ours["instance"]]["level"]
    for level in ours["levels"]:
        genie_lsps = genie_levels[_LEVEL_NUMBER[level["level"]]]["lspid"]
        assert [lsp["lsp_id"] for lsp in level["lsps"]] == list(genie_lsps)
        for lsp in level["lsps"]:
            genie_lsp = genie_lsps[lsp["lsp_id"]]["lsp"]
            assert lsp["sequence_number"] == genie_lsp["seq_num"]
            assert lsp["checksum"] == genie_lsp["checksum"]
            assert lsp["holdtime_sec"] == genie_lsp["holdtime"]
            assert lsp["own_lsp"] == genie_lsp["local_router"]
            assert lsp["att_p_ol"] == (
                f"{genie_lsp['attach_bit']}/{genie_lsp['p_bit']}/{genie_lsp['overload_bit']}"
            )
