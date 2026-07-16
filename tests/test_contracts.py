from execution_proxy.contracts import (
    DeviceCredentials,
    DeviceResult,
    ErrorCode,
    OperationError,
)


def test_success_result_matches_normalized_contract():
    result = DeviceResult(
        device="router2",
        operation="get_interface_status",
        platform="frr",
        status="success",
        data={
            "interface": "eth2",
            "admin_up": True,
            "oper_up": False,
            "addresses": ["10.0.23.2/30"],
        },
        duration_ms=184,
    )

    assert result.as_dict() == {
        "device": "router2",
        "operation": "get_interface_status",
        "platform": "frr",
        "status": "success",
        "data": {
            "interface": "eth2",
            "admin_up": True,
            "oper_up": False,
            "addresses": ["10.0.23.2/30"],
        },
        "duration_ms": 184,
    }


def test_error_result_is_structured_and_has_no_raw_output():
    result = DeviceResult(
        device="router6",
        operation="get_ospf_status",
        platform="frr",
        status="error",
        data=None,
        duration_ms=5000,
        error=OperationError(
            code=ErrorCode.DEVICE_UNREACHABLE,
            message="device unreachable",
        ),
    )

    assert result.as_dict() == {
        "device": "router6",
        "operation": "get_ospf_status",
        "platform": "frr",
        "status": "error",
        "data": None,
        "duration_ms": 5000,
        "error": {
            "code": "device_unreachable",
            "message": "device unreachable",
        },
    }


def test_credentials_repr_does_not_expose_secrets():
    credentials = DeviceCredentials(
        username="diag",
        authentication_type="password",
        password="do-not-print",
    )

    assert "diag" not in repr(credentials)
    assert "do-not-print" not in repr(credentials)

