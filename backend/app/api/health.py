from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyStatus(BaseModel):
    status: Literal["ok", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    checks: dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report process liveness without contacting dependencies."""
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report whether dependencies required for core coordination are reachable."""
    database_ready = await request.app.state.database.is_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unavailable", checks={"database": DependencyStatus(status="unavailable")}
        )
    return ReadinessResponse(status="ready", checks={"database": DependencyStatus(status="ok")})
