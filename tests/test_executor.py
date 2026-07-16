import json
import time

from execution_proxy.contracts import (
    DeviceCredentials,
    DeviceProfile,
    ErrorCode,
    ExecutionError,
    OperationRequest,
)
from execution_proxy.executor import BatchExecutor


class Inventory:
    def get_device(self, device_name):
        if device_name == "missing":
            raise ExecutionError(ErrorCode.DEVICE_NOT_FOUND, "device not found")
        return DeviceProfile(
            name=device_name,
            host="172.20.20.11",
            port=22,
            platform="frr",
            credential_profile="demo-frr-readonly",
            interfaces=frozenset({"eth1"}),
        )


class Credentials:
    def get_credentials(self, _credential_profile):
        return DeviceCredentials(
            username="diag",
            authentication_type="password",
            password="secret",
        )


class Adapter:
    def __init__(self, device_name, *, delay_sec=0):
        self.device_name = device_name
        self.delay_sec = delay_sec

    def run(self, operation, **arguments):
        time.sleep(self.delay_sec)
        return {"device": self.device_name, "arguments": arguments}


def test_batch_returns_success_and_structured_partial_failure():
    executor = BatchExecutor(
        Inventory(),
        Credentials(),
        {"frr": lambda device, _credentials: Adapter(device.name)},
    )
    try:
        results = executor.execute(
            OperationRequest(
                operation="get_interface_status",
                devices=("router1", "missing"),
                arguments={"interface": "eth1"},
            )
        )
    finally:
        executor.close()

    assert [result.status for result in results] == ["success", "error"]
    assert results[0].data == {
        "device": "router1",
        "arguments": {"interface": "eth1"},
    }
    assert results[1].error.code == ErrorCode.DEVICE_NOT_FOUND


def test_whole_request_deadline_returns_without_waiting_for_slow_device():
    executor = BatchExecutor(
        Inventory(),
        Credentials(),
        {"frr": lambda device, _credentials: Adapter(device.name, delay_sec=0.2)},
        request_deadline_sec=0.03,
    )
    started_at = time.monotonic()
    try:
        results = executor.execute(
            OperationRequest(
                operation="get_ospf_neighbors",
                devices=("router1",),
            )
        )
    finally:
        executor.close(wait=False)

    assert time.monotonic() - started_at < 0.15
    assert results[0].error.code == ErrorCode.DEADLINE_EXCEEDED


def test_execution_emits_one_audit_record_per_device_without_secrets(caplog):
    executor = BatchExecutor(
        Inventory(),
        Credentials(),
        {"frr": lambda device, _credentials: Adapter(device.name)},
    )
    try:
        with caplog.at_level("INFO", logger="execution_proxy.audit"):
            executor.execute(
                OperationRequest(
                    operation="get_interface_status",
                    devices=("router1", "missing"),
                    arguments={"interface": "eth1"},
                    request_id="req-1",
                )
            )
    finally:
        executor.close()

    records = [json.loads(message) for message in caplog.messages]
    assert len(records) == 2
    by_device = {record["device"]: record for record in records}
    assert by_device["router1"]["status"] == "success"
    assert by_device["router1"]["request_id"] == "req-1"
    assert by_device["router1"]["operation"] == "get_interface_status"
    assert by_device["router1"]["arguments"] == {"interface": "eth1"}
    assert by_device["missing"]["status"] == "error"
    assert by_device["missing"]["error_code"] == "device_not_found"
    for record in records:
        serialized = json.dumps(record)
        assert "secret" not in serialized
        assert "password" not in serialized


def test_unsupported_platform_fails_before_credentials_are_used():
    class JunosInventory(Inventory):
        def get_device(self, device_name):
            device = super().get_device(device_name)
            return DeviceProfile(**{**device.__dict__, "platform": "junos"})

    executor = BatchExecutor(JunosInventory(), Credentials(), {})
    try:
        result = executor.execute(
            OperationRequest(
                operation="get_ospf_neighbors",
                devices=("router1",),
            )
        )[0]
    finally:
        executor.close()

    assert result.error.code == ErrorCode.UNSUPPORTED_PLATFORM
