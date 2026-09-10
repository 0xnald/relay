from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyStatus(BaseModel):
    status: Literal["not_checked"] = "not_checked"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    dependencies: dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report process liveness without contacting dependencies."""
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    """Report readiness; dependency probes will be added with runtime infrastructure."""
    return ReadinessResponse(dependencies={"database": DependencyStatus()})
