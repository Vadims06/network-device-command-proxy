"""Literal-expectation tests for the IOS XR IS-IS database parser,
hand-verified against the copied fixture - never derived from the parser
under test."""
import os

import device_command_proxy
from device_command_proxy.platforms.iosxr.isis_database_parser import (
    parse_isis_database_detail,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(device_command_proxy.__file__), "fixtures", "captured", "cisco_iosxr"
)


def _read_fixture(name):
    with open(os.path.join(_FIXTURE_DIR, name)) as f:
        return f.read()


def test_instance_and_level_lsp_counts():
    """The device dumps its Level-1 and Level-2 databases as separate
    sections; a flat merge would lose which level an LSP belongs to."""
    result = parse_isis_database_detail(_read_fixture("show_isis_database_detail.txt"))

    assert result["instance"] == "test"
    assert [level["level"] for level in result["levels"]] == ["Level-1", "Level-2"]
    assert [len(level["lsps"]) for level in result["levels"]] == [11, 11]


def test_own_lsp_and_first_row_fields():
    result = parse_isis_database_detail(_read_fixture("show_isis_database_detail.txt"))
    first_lsp = result["levels"][0]["lsps"][0]

    assert first_lsp == {
        "lsp_id": "R3.00-00",
        "own_lsp": True,
        "sequence_number": "0x0000000d",
        "checksum": "0x0476",
        "holdtime_sec": 578,
        "att_p_ol": "1/0/0",
    }
    assert result["levels"][0]["lsps"][1]["own_lsp"] is False
