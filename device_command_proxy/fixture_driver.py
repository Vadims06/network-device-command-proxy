"""Replays a captured CLI response instead of opening SSH.

Used only by devices whose inventory entry sets transport=fixture. The
returned object matches what Scrapli's own driver gives `_send_command`
(`.result`, `.failed`), so every vendor adapter's parsing code runs unchanged
against captured text - a fixture answer proves the parser, not a shortcut
around it.
"""

from __future__ import annotations

import json
from pathlib import Path

from device_command_proxy.contracts import ErrorCode, ExecutionError

_FIXTURES_ROOT = Path(__file__).parent / "fixtures"
_DEMO_DIR = _FIXTURES_ROOT / "demo"


class _FixtureResponse:
    def __init__(self, result: str):
        self.result = result
        self.failed = False


class _FixtureSession:
    def __init__(self, device_name: str):
        self._commands = _load_command_map(device_name)

    def __enter__(self) -> "_FixtureSession":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def send_command(self, command: str) -> _FixtureResponse:
        captured_path = self._commands.get(command)
        if captured_path is None:
            raise ExecutionError(
                ErrorCode.FIXTURE_NOT_FOUND,
                f"no demo fixture captured for command {command!r}",
            )
        return _FixtureResponse((_FIXTURES_ROOT / captured_path).read_text())


def _load_command_map(device_name: str) -> dict[str, str]:
    path = _DEMO_DIR / f"{device_name}.json"
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exception:
        raise ExecutionError(
            ErrorCode.FIXTURE_NOT_FOUND,
            f"device {device_name!r} has no demo fixture map",
        ) from exception


def create_fixture_driver(device_name: str) -> _FixtureSession:
    return _FixtureSession(device_name)
