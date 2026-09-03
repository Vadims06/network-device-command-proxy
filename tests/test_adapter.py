from contextlib import nullcontext

import pytest

from device_command_proxy.contracts import ErrorCode, ExecutionError
from device_command_proxy.operation_types import Operation
from device_command_proxy.platforms.base import DeviceAdapter, OutputFormat


class FakeDriver:
    def __init__(self, result):
        self._result = result

    def send_command(self, _command):
        return type("FakeResponse", (), {"result": self._result, "failed": False})()


def test_text_output_is_available_to_operation_parsers():
    adapter = DeviceAdapter(lambda: nullcontext(FakeDriver("Interface eth0\n")))
    adapter._operation_handlers = {
        Operation.GET_OSPF_NEIGHBORS: lambda: {
            "instance": None,
            "neighbors": [],
        }
    }

    assert adapter._send_command(
        "show thing", output_format=OutputFormat.TEXT
    ) == "Interface eth0\n"


def test_json_output_is_decoded_by_shared_transport():
    adapter = DeviceAdapter(lambda: nullcontext(FakeDriver('{"a": 1}')))

    assert adapter._send_command("show thing") == {"a": 1}


def test_invalid_json_is_a_parse_error_when_operation_runs():
    adapter = DeviceAdapter(lambda: nullcontext(FakeDriver("not json")))
    adapter._operation_handlers = {
        Operation.GET_OSPF_NEIGHBORS: lambda: adapter._send_command("show thing")
    }

    with pytest.raises(ExecutionError) as raised_error:
        adapter.run(Operation.GET_OSPF_NEIGHBORS)

    assert raised_error.value.code == ErrorCode.PARSE_ERROR


def test_authentication_failure_is_reported_distinctly_from_unreachable():
    from scrapli.exceptions import ScrapliAuthenticationFailed

    class FailingDriverFactory:
        def __enter__(self):
            raise ScrapliAuthenticationFailed("all authentication methods failed")

        def __exit__(self, *_exc_info):
            return False

    adapter = DeviceAdapter(lambda: FailingDriverFactory())

    with pytest.raises(ExecutionError) as raised_error:
        adapter._send_command("show thing")

    assert raised_error.value.code == ErrorCode.AUTHENTICATION_FAILED


def test_command_failure_is_reported_distinctly_from_unreachable():
    class FailedResponseDriver:
        def send_command(self, _command):
            return type("FakeResponse", (), {"result": "", "failed": True})()

    adapter = DeviceAdapter(lambda: nullcontext(FailedResponseDriver()))

    with pytest.raises(ExecutionError) as raised_error:
        adapter._send_command("show thing")

    assert raised_error.value.code == ErrorCode.COMMAND_FAILED


def test_invalid_device_output_is_not_written_to_the_warning_log(caplog):
    adapter = DeviceAdapter(lambda: nullcontext(FakeDriver("unused")))
    adapter._operation_handlers = {
        Operation.GET_OSPF_NEIGHBORS: lambda: (_ for _ in ()).throw(
            ValueError("device-secret-output")
        )
    }

    with caplog.at_level("WARNING", logger="device_command_proxy.platforms.base"):
        with pytest.raises(ExecutionError):
            adapter.run(Operation.GET_OSPF_NEIGHBORS)

    assert "device-secret-output" not in caplog.text
    assert "ValueError" in caplog.text
