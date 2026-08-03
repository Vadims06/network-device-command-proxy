"""The public models, generated OpenAPI and drivers must agree."""

from contextlib import nullcontext
import json

import jsonschema
import pytest

from device_command_proxy.api import create_app
from device_command_proxy.operation_types import Operation
from device_command_proxy.operations import OPERATION_SPECS
from device_command_proxy.platforms import PLATFORMS, UNSUPPORTED_FIELDS
from device_command_proxy.platforms.frr.driver import FrrAdapter
from device_command_proxy.platforms.junos.driver import JunosAdapter
from tests.golden_device_output import FRR_OUTPUT, JUNOS_OUTPUT, OPERATION_ARGUMENTS


class FakeExecutor:
    def execute(self, _request):
        return ()


SPECIFICATION = create_app(FakeExecutor(), "token").openapi()
SCHEMAS = SPECIFICATION["components"]["schemas"]
ADAPTERS = {"frr": FrrAdapter, "junos": JunosAdapter}
PLATFORM_OUTPUT = {"frr": FRR_OUTPUT, "junos": JUNOS_OUTPUT}
PLATFORM_OPERATIONS = [
    (platform, operation)
    for platform in ADAPTERS
    for operation in OPERATION_SPECS
]


class FakeDriver:
    def __init__(self, payload):
        self._payload = payload

    def send_command(self, _command):
        return type(
            "FakeResponse", (), {"result": json.dumps(self._payload), "failed": False}
        )()


def _run(platform: str, operation: Operation):
    adapter = ADAPTERS[platform](
        lambda: nullcontext(FakeDriver(PLATFORM_OUTPUT[platform][operation.value]))
    )
    return adapter.run(
        operation,
        **OPERATION_ARGUMENTS[platform].get(operation.value, {}),
    )


@pytest.mark.parametrize("platform,operation", PLATFORM_OPERATIONS)
def test_driver_output_matches_the_public_model(platform, operation):
    result = _run(platform, operation)

    validated = OPERATION_SPECS[operation].response_model.model_validate(result)

    assert validated.model_dump(mode="json") == result


@pytest.mark.parametrize("platform,operation", PLATFORM_OPERATIONS)
def test_driver_output_validates_against_generated_openapi(platform, operation):
    result = _run(platform, operation)
    schema_name = OPERATION_SPECS[operation].response_model.__name__

    jsonschema.validate(
        result,
        _inline_refs({"$ref": f"#/components/schemas/{schema_name}"}),
    )


@pytest.mark.parametrize("platform,operation", PLATFORM_OPERATIONS)
def test_both_platforms_produce_identical_key_sets(platform, operation):
    assert _key_shape(_run(platform, operation)) == _key_shape(
        _run("frr", operation)
    )


def _key_shape(value):
    if isinstance(value, dict):
        return {name: _key_shape(child) for name, child in sorted(value.items())}
    if isinstance(value, list):
        return [_key_shape(item) for item in value[:1]]
    return None


@pytest.mark.parametrize("platform,operation", PLATFORM_OPERATIONS)
def test_declared_unsupported_fields_are_null(platform, operation):
    result = _run(platform, operation)

    for field in UNSUPPORTED_FIELDS.get(platform, {}).get(operation, ()):
        values = _field_values(result, field)
        assert values
        assert all(value is None for value in values)


def _field_values(value, field):
    if isinstance(value, dict):
        found = [value[field]] if field in value else []
        return found + [
            nested
            for child in value.values()
            for nested in _field_values(child, field)
        ]
    if isinstance(value, list):
        return [nested for item in value for nested in _field_values(item, field)]
    return []


def _inline_refs(node):
    if isinstance(node, dict):
        if set(node) == {"$ref"}:
            return _inline_refs(SCHEMAS[node["$ref"].rsplit("/", 1)[1]])
        return {key: _inline_refs(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline_refs(value) for value in node]
    return node


def _envelope(*, status, operation, data=None, error=None):
    result = {
        "device": "router1",
        "operation": operation.value,
        "platform": "frr",
        "status": status,
        "data": data,
        "duration_ms": 10,
        "unsupported_fields": [],
    }
    if error is not None:
        result["error"] = error
    return result


def test_generated_openapi_publishes_operation_enum():
    assert set(SCHEMAS["ExecuteRequest"]["properties"]["operation"]["enum"]) == {
        operation.value for operation in Operation
    }
    assert SCHEMAS["DeviceResultModel"]["discriminator"]["propertyName"] == "status"
    assert set(SCHEMAS["Operation"]["enum"]) == {
        operation.value for operation in Operation
    }


def test_success_envelope_with_driver_data_is_valid():
    jsonschema.validate(
        _envelope(
            status="success",
            operation=Operation.GET_OSPF_NEIGHBORS,
            data=_run("frr", Operation.GET_OSPF_NEIGHBORS),
        ),
        _inline_refs(SCHEMAS["DeviceResultModel"]),
    )


def test_response_with_an_unknown_operation_is_rejected():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _envelope(
                status="success",
                operation=Operation.GET_OSPF_NEIGHBORS,
                data={"instance": None, "neighbors": []},
            ) | {"operation": "unknown"},
            _inline_refs(SCHEMAS["DeviceResultModel"]),
        )


def test_response_operation_selects_matching_data_schema():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _envelope(
                status="success",
                operation=Operation.GET_ROUTE,
                data=_run("frr", Operation.GET_OSPF_NEIGHBORS),
            ),
            _inline_refs(SCHEMAS["DeviceResultModel"]),
        )


def test_error_envelope_requires_error_without_data():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _envelope(status="error", operation=Operation.GET_ROUTE),
            _inline_refs(SCHEMAS["DeviceResultModel"]),
        )


def test_success_envelope_requires_data_without_error():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            _envelope(
                status="success",
                operation=Operation.GET_ROUTE,
                data=None,
                error={"code": "internal_error", "message": "failed"},
            ),
            _inline_refs(SCHEMAS["DeviceResultModel"]),
        )


def test_registry_covers_every_registered_platform_and_operation():
    assert set(ADAPTERS) == set(PLATFORMS)
    assert set(OPERATION_SPECS) == set(Operation)
    for platform in PLATFORM_OUTPUT:
        assert set(PLATFORM_OUTPUT[platform]) == {operation.value for operation in Operation}


@pytest.mark.parametrize("platform", ["frr", "junos"])
def test_singular_ospf_interface_operation_allows_empty_result(platform):
    empty = {"interfaces": {}} if platform == "frr" else {}
    adapter = ADAPTERS[platform](lambda: nullcontext(FakeDriver(empty)))

    assert adapter.run(
        Operation.GET_OSPF_INTERFACE,
        **OPERATION_ARGUMENTS[platform][Operation.GET_OSPF_INTERFACE.value],
    ) == {"interfaces": []}
