import json

import pytest

from device_command_proxy import audit
from device_command_proxy.contracts import DeviceResult


def _result(**overrides):
    defaults = dict(
        device="router1",
        operation="get_interface_status",
        platform="frr",
        status="success",
        data={"interface": "eth0"},
        duration_ms=5,
    )
    return DeviceResult(**{**defaults, **overrides})


def test_only_known_argument_keys_are_recorded(caplog):
    # An authenticated caller can put anything in `arguments`; the operation
    # being rejected for it must not also get it logged verbatim.
    with caplog.at_level("INFO", logger="device_command_proxy.audit"):
        audit.record(
            _result(),
            request_id="req-1",
            arguments={"interface": "eth0", "password": "supersecret"},
        )

    entry = json.loads(caplog.messages[0])
    assert entry["arguments"] == {"interface": "[redacted]"}
    assert "password" not in json.dumps(entry)
    assert "supersecret" not in json.dumps(entry)


@pytest.mark.parametrize(
    "key, value", [("interface", "eth0"), ("prefix", "10.0.0.0/24")]
)
def test_legitimate_argument_keys_are_recorded(caplog, key, value):
    with caplog.at_level("INFO", logger="device_command_proxy.audit"):
        audit.record(_result(), request_id="", arguments={key: value})

    entry = json.loads(caplog.messages[0])
    assert entry["arguments"] == {key: "[redacted]"}


@pytest.mark.parametrize("key, value", [("interface", "SuperSecretPassword"), ("prefix", "supersecret")])
def test_argument_values_are_never_recorded(caplog, key, value):
    with caplog.at_level("INFO", logger="device_command_proxy.audit"):
        audit.record(_result(), request_id="req-1", arguments={key: value})

    entry = json.loads(caplog.messages[0])
    assert entry["arguments"] == {key: "[redacted]"}
    assert value not in json.dumps(entry)


def test_request_id_is_hashed_before_it_is_logged(caplog):
    secret_request_id = "password-token-value"

    with caplog.at_level("INFO", logger="device_command_proxy.audit"):
        audit.record(_result(), request_id=secret_request_id, arguments={})

    entry = json.loads(caplog.messages[0])
    assert entry["request_id"] != secret_request_id
    assert secret_request_id not in caplog.messages[0]
