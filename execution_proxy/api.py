"""Authenticated REST boundary for semantic device operations."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from execution_proxy.contracts import ExecutionError, OperationRequest
from execution_proxy.executor import BatchExecutor


class ExecuteRequest(BaseModel):
    operation: str
    devices: list[str]
    arguments: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default="", max_length=128)


def create_app(executor: BatchExecutor, bearer_token: str) -> FastAPI:
    if not bearer_token:
        raise ValueError("bearer token is required")
    app = FastAPI(title="execution-proxy", docs_url=None, redoc_url=None)

    async def authorize(authorization: str = Header(default="")) -> None:
        expected = f"Bearer {bearer_token}"
        if not secrets.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/execute", dependencies=[Depends(authorize)])
    async def execute(request: ExecuteRequest) -> dict[str, Any]:
        try:
            results = executor.execute(
                OperationRequest(
                    operation=request.operation,
                    devices=tuple(request.devices),
                    arguments=request.arguments,
                    request_id=request.request_id,
                )
            )
        except ExecutionError as exception:
            raise HTTPException(
                status_code=400,
                detail={"code": exception.code.value, "message": str(exception)},
            ) from exception
        return {
            "request_id": request.request_id,
            "results": [result.as_dict() for result in results],
        }

    return app
