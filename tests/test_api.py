import asyncio
import inspect

import httpx

from execution_proxy.api import create_app
from execution_proxy.contracts import DeviceResult


class Executor:
    def execute(self, request):
        return (
            DeviceResult(
                device=request.devices[0],
                operation=request.operation,
                platform="frr",
                status="success",
                data={"neighbors": []},
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
                "data": {"neighbors": []},
                "duration_ms": 4,
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
