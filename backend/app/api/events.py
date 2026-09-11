from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Header, Request

from app.core.errors import RescueNotFound
from app.schemas.events import EventIngestRequest, EventProcessingResponse, EventResponse
from app.schemas.rescues import RescueResponse
from app.services.event_processing import EventIngestionService, UnitOfWorkFactory

router = APIRouter(prefix="/api/v1", tags=["rescue coordination"])
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    ),
]


def uow_factory(request: Request) -> UnitOfWorkFactory:
    return cast(UnitOfWorkFactory, request.app.state.uow_factory)


@router.post("/events", response_model=EventProcessingResponse)
async def ingest_event(
    body: EventIngestRequest,
    request: Request,
    idempotency_key: IdempotencyKey,
) -> EventProcessingResponse:
    event = body.to_domain(
        idempotency_key=idempotency_key,
        trace_id=cast(str, request.state.trace_id),
    )
    result = await EventIngestionService(uow_factory(request)).process(event)
    return EventProcessingResponse.from_result(result)


@router.get("/rescues/{rescue_id}", response_model=RescueResponse)
async def get_rescue(rescue_id: UUID, request: Request) -> RescueResponse:
    async with uow_factory(request)() as uow:
        rescue = await uow.rescues.get(rescue_id)
    if rescue is None:
        raise RescueNotFound()
    return RescueResponse.from_domain(rescue)


@router.get("/rescues/{rescue_id}/events", response_model=list[EventResponse])
async def get_rescue_events(rescue_id: UUID, request: Request) -> list[EventResponse]:
    async with uow_factory(request)() as uow:
        rescue = await uow.rescues.get(rescue_id)
        if rescue is None:
            raise RescueNotFound()
        events = await uow.events.list_for_rescue(rescue_id)
    return [EventResponse.from_domain(event) for event in events]
