import asyncio
import inspect

import httpx

from device_command_proxy.api import create_app
from device_command_proxy.contracts import DeviceResult, ErrorCode, ExecutionError


class Executor:
    def execute(self, request):
        return (
            DeviceResult(
                device=request.devices[0],
                operation=request.operation,
                platform="frr",
                status="success",
                data={"instance": None, "neighbors": []},
                duration_ms=4,
            ),
        )


def test_execute_requires_static_bearer_token_and_returns_stable_contract():
    async def exercise_app():
        app = create_app(Executor(), "mcp-to-proxy-token")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://execution-proxy",
        ) as client:
            payload = {
                "operation": "get_ospf_neighbors",
                "devices": ["router1"],
                "request_id": "session-1",
            }
            unauthorized = await client.post("/v1/execute", json=payload)
            response = await client.post(
                "/v1/execute",
                json=payload,
                headers={"Authorization": "Bearer mcp-to-proxy-token"},
            )
        return unauthorized, response

    unauthorized, response = asyncio.run(exercise_app())

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json() == {
        "request_id": "session-1",
        "results": [
            {
                "device": "router1",
                "operation": "get_ospf_neighbors",
                "platform": "frr",
                "status": "success",
                "data": {"instance": None, "neighbors": []},
                "duration_ms": 4,
                "unsupported_fields": [],
                "data_source": "unknown",
            }
        ],
    }


def test_execute_endpoint_is_sync_so_fastapi_runs_it_in_the_threadpool():
    # A coroutine endpoint would block the event loop for the full
    # executor.execute() wait, freezing every concurrent request.
    app = create_app(Executor(), "mcp-to-proxy-token")
    execute_route = next(
        route for route in app.routes if getattr(route, "path", None) == "/v1/execute"
    )

    assert not inspect.iscoroutinefunction(execute_route.endpoint)


def test_request_level_rejection_becomes_a_400_carrying_its_error_code():
    # An unknown operation is rejected by the executor before any device is
    # contacted; this layer's job is turning that into the documented 400
    # envelope rather than a per-device result.
    class RejectingExecutor:
        def execute(self, _request):
            raise ExecutionError(
                ErrorCode.UNSUPPORTED_OPERATION, "operation is not allowed"
            )

    async def exercise_app():
        app = create_app(RejectingExecutor(), "mcp-to-proxy-token")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://execution-proxy"
        ) as client:
            return await client.post(
                "/v1/execute",
                json={"operation": "run_command", "devices": ["router1"]},
                headers={"Authorization": "Bearer mcp-to-proxy-token"},
            )

    response = asyncio.run(exercise_app())

    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "unsupported_operation",
        "message": "operation is not allowed",
    }


def test_documentation_is_served_from_the_committed_spec():
    # The documentation endpoint and conformance tests use the same generated contract.
    async def exercise_app():
        app = create_app(Executor(), "mcp-to-proxy-token")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://execution-proxy"
        ) as client:
            return (
                await client.get("/openapi.json"),
                await client.get("/docs"),
                await client.get("/openapi.json"),
            )

    specification, documentation, generated = asyncio.run(exercise_app())

    assert specification.status_code == 200
    assert "application/json" in specification.headers["content-type"]
    assert "get_ospf_interfaces" in specification.text
    assert documentation.status_code == 200
    assert "/openapi.json" in documentation.text
    assert generated.status_code == 200


def test_openapi_documents_error_responses_and_bearer_authentication():
    specification = create_app(Executor(), "mcp-to-proxy-token").openapi()
    operation = specification["paths"]["/v1/execute"]["post"]

    assert operation["security"] == [{"HTTPBearer": []}]
    assert operation["responses"]["400"]["content"]["application/json"]["schema"][
        "$ref"
    ] == "#/components/schemas/BadRequestResponseModel"
    assert operation["responses"]["401"]["content"]["application/json"]["schema"][
        "$ref"
    ] == "#/components/schemas/UnauthorizedResponseModel"


def test_openapi_rejects_a_raw_request_id_that_exceeds_the_contract():
    async def exercise_app():
        app = create_app(Executor(), "mcp-to-proxy-token")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://execution-proxy"
        ) as client:
            return await client.post(
                "/v1/execute",
                json={
                    "operation": "get_ospf_neighbors",
                    "devices": ["router1"],
                    "request_id": "x" * 129,
                },
                headers={"Authorization": "Bearer mcp-to-proxy-token"},
            )

    assert asyncio.run(exercise_app()).status_code == 422
