from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.domain.network import HumanReviewRequest, OperationalException
from app.domain.organizations import Driver, Recipient
from app.domain.rescue import Assignment, RescueAllocation
from app.repositories.network import NetworkStore
from app.services.event_processing import EventIngestionService, UnitOfWorkFactory
from app.services.human_review import HumanReviewService

router = APIRouter(prefix="/api/v1", tags=["rescue network"])


class ResolveDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolution: str = Field(min_length=1, max_length=1000)
    actor_id: UUID


@router.get("/network/recipients", response_model=list[Recipient])
async def list_recipients(request: Request) -> list[Recipient]:
    return await cast(NetworkStore, request.app.state.network_store).list_recipients()


@router.get("/network/drivers", response_model=list[Driver])
async def list_drivers(request: Request) -> list[Driver]:
    return await cast(NetworkStore, request.app.state.network_store).list_drivers()


@router.get("/rescues/{rescue_id}/allocations", response_model=list[RescueAllocation])
async def list_allocations(rescue_id: UUID, request: Request) -> list[RescueAllocation]:
    return await cast(NetworkStore, request.app.state.network_store).list_allocations(rescue_id)


@router.get("/rescues/{rescue_id}/assignments", response_model=list[Assignment])
async def list_assignments(rescue_id: UUID, request: Request) -> list[Assignment]:
    return await cast(NetworkStore, request.app.state.network_store).list_assignments(rescue_id)


@router.get("/rescues/{rescue_id}/exceptions", response_model=list[OperationalException])
async def list_exceptions(rescue_id: UUID, request: Request) -> list[OperationalException]:
    return await cast(NetworkStore, request.app.state.network_store).list_exceptions(rescue_id)


@router.get("/decisions", response_model=list[HumanReviewRequest])
async def list_decisions(request: Request) -> list[HumanReviewRequest]:
    return await cast(NetworkStore, request.app.state.network_store).list_decisions()


@router.get("/decisions/{decision_id}", response_model=HumanReviewRequest)
async def get_decision(decision_id: UUID, request: Request) -> HumanReviewRequest:
    decisions = await cast(NetworkStore, request.app.state.network_store).list_decisions()
    decision = next((item for item in decisions if item.id == decision_id), None)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision request not found")
    return decision


@router.post("/decisions/{decision_id}/resolve", response_model=HumanReviewRequest)
async def resolve_decision(
    decision_id: UUID, body: ResolveDecisionRequest, request: Request
) -> HumanReviewRequest:
    store = cast(NetworkStore, request.app.state.network_store)
    uow_factory = cast(UnitOfWorkFactory, request.app.state.uow_factory)
    result, _ = await HumanReviewService(store, EventIngestionService(uow_factory)).resolve(
        decision_id,
        resolution=body.resolution,
        actor_id=body.actor_id,
        trace_id=cast(str, request.state.trace_id),
    )
    return result
