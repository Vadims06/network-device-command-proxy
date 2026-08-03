import json
import hashlib
import logging

import pytest
from scrapli.exceptions import ScrapliConnectionError

from device_command_proxy import audit, config
from device_command_proxy.contracts import DeviceResult, ErrorCode, ExecutionError
from device_command_proxy.operation_types import Operation
from device_command_proxy.platforms.base import DeviceAdapter


def _failing_adapter(exception: Exception) -> DeviceAdapter:
    def driver_factory():
        raise exception

    adapter = DeviceAdapter(driver_factory)
    adapter._operation_handlers = {
        Operation.GET_OSPF_NEIGHBORS: lambda: adapter._send_command(
            "show ip ospf neighbor json"
        )
    }
    return adapter


def test_a_local_setup_fault_is_logged_not_only_reported_as_unreachable(caplog):
    # A missing ssh-keyscan raises FileNotFoundError here. It is an OSError,
    # so the caller sees the same device_unreachable as a device that is down;
    # the log is the only thing that tells the two apart.
    adapter = _failing_adapter(FileNotFoundError(2, "No such file", "ssh-keyscan"))

    with caplog.at_level(logging.WARNING, logger="device_command_proxy.platforms.base"):
        with pytest.raises(ExecutionError) as raised:
            adapter.run("get_ospf_neighbors")

    assert raised.value.code == ErrorCode.DEVICE_UNREACHABLE
    assert "FileNotFoundError" in caplog.text
    assert "ssh-keyscan" in caplog.text


def test_a_genuine_transport_failure_is_logged_with_its_type(caplog):
    adapter = _failing_adapter(ScrapliConnectionError("connection refused"))

    with caplog.at_level(logging.WARNING, logger="device_command_proxy.platforms.base"):
        with pytest.raises(ExecutionError):
            adapter.run("get_ospf_neighbors")

    assert "ScrapliConnectionError" in caplog.text
    assert "connection refused" in caplog.text


def test_configure_logging_lets_audit_records_reach_stdout(monkeypatch, capsys):
    # uvicorn leaves the root logger without a handler, so the package logger
    # has to carry its own or every audit entry is dropped.
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    config.configure_logging()

    audit.record(
        DeviceResult(
            device="router1",
            operation="get_ospf_neighbors",
            platform="frr",
            status="success",
            data={},
            duration_ms=12,
        ),
        request_id="abc",
        arguments={},
    )

    logged = capsys.readouterr().out
    assert "device_command_proxy.audit" in logged
    entry = json.loads(logged[logged.index("{") :])
    assert entry["device"] == "router1"
    assert entry["request_id"] == hashlib.sha256(b"abc").hexdigest()


def test_configure_logging_is_idempotent_across_repeated_imports(monkeypatch, capsys):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    config.configure_logging()
    config.configure_logging()

    logging.getLogger("device_command_proxy.audit").info("once")

    assert capsys.readouterr().out.count("once") == 1


def test_log_level_is_configurable(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    config.configure_logging()

    logging.getLogger("device_command_proxy.audit").info("suppressed")

    assert "suppressed" not in capsys.readouterr().out
