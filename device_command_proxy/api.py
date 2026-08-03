"""Authenticated REST boundary for semantic device operations."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from device_command_proxy.contracts import ExecutionError, OperationRequest
from device_command_proxy.operation_types import Operation
from device_command_proxy.schemas import (
    BadRequestResponseModel,
    ExecuteResponseModel,
    UnauthorizedResponseModel,
)


class ExecuteRequest(BaseModel):
    operation: str = Field(
        json_schema_extra={"enum": [operation.value for operation in Operation]}
    )
    devices: list[str]
    arguments: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default="", max_length=128)


def create_app(executor, bearer_token: str) -> FastAPI:
    if not bearer_token:
        raise ValueError("bearer token is required")

    app = FastAPI(
        title="execution-proxy",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    def authorize(authorization: str) -> None:
        provided_token = authorization.removeprefix("Bearer ").strip()
        if not secrets.compare_digest(provided_token, bearer_token):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/v1/execute",
        response_model=ExecuteResponseModel,
        openapi_extra={"security": [{"HTTPBearer": []}]},
        responses={
            400: {"model": BadRequestResponseModel},
            401: {"model": UnauthorizedResponseModel},
        },
    )
    def execute(
        request: ExecuteRequest,
        authorization: str = Header(default="", include_in_schema=False),
    ) -> dict[str, Any]:
        authorize(authorization)
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
        response = {
            "request_id": request.request_id,
            "results": [result.as_dict() for result in results],
        }
        ExecuteResponseModel.model_validate(response)
        return JSONResponse(content=response)

    original_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        specification = original_openapi()
        specification.setdefault("components", {}).setdefault("securitySchemes", {})[
            "HTTPBearer"
        ] = {"type": "http", "scheme": "bearer"}
        return specification

    app.openapi = openapi

    return app
