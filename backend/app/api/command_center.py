from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.domain.enums import AssignmentStatus, RescueStatus
from app.models.foundational import RescueRecord
from app.models.network import DonationRecord, DonorRecord, FoodItemRecord
from app.repositories.network import NetworkStore
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.demo_network import seed_demo_network
from app.workflows.hero import run_hero_scenario

router = APIRouter(prefix="/api/v1", tags=["command center"])


def _time(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _rescue_overview(request: Request, rescue: RescueRecord) -> dict[str, Any]:
    store = cast(NetworkStore, request.app.state.network_store)
    if rescue.donation_id is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Rescue donation is missing")
    donation = await store.get_donation(rescue.donation_id)
    if donation is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Rescue donation is missing")
    donor = await store.get_donor(donation.donor_id)
    allocations = await store.list_allocations(rescue.id)
    assignments = await store.list_assignments(rescue.id)
    exceptions = await store.list_exceptions(rescue.id)
    recipients = {item.id: item.name for item in await store.list_recipients()}
    drivers = {item.id: item.name for item in await store.list_drivers()}
    items = await store.list_food_items(donation.id)
    active_allocations = [
        item for item in allocations if item.status is not AssignmentStatus.CANCELLED
    ]
    return {
        "id": str(rescue.id),
        "short_code": str(rescue.id).split("-")[0].upper(),
        "status": rescue.status,
        "donor": donor.name if donor else "Unknown donor",
        "pickup_deadline": _time(donation.pickup_window_end),
        "food_summary": ", ".join(f"{item.quantity} {item.unit} {item.name}" for item in items),
        "food_quantity": sum(float(item.quantity) for item in items),
        "recipients": sorted(
            {recipients.get(item.recipient_id, "Unknown") for item in active_allocations}
        ),
        "drivers": sorted(
            {
                drivers.get(item.driver_id, "Unknown")
                for item in assignments
                if item.status is not AssignmentStatus.CANCELLED
            }
        ),
        "exception_count": len(exceptions),
        "progress": 100 if rescue.status == RescueStatus.COMPLETED.value else 65,
        "updated_at": _time(rescue.updated_at),
    }


@router.get("/dashboard")
async def dashboard(request: Request) -> dict[str, Any]:
    database = request.app.state.database
    async with database.session_factory() as session:
        rescues = (
            await session.scalars(select(RescueRecord).order_by(RescueRecord.updated_at.desc()))
        ).all()
    overviews = [await _rescue_overview(request, rescue) for rescue in rescues]
    store = cast(NetworkStore, request.app.state.network_store)
    decisions = await store.list_decisions()
    active = [item for item in overviews if item["status"] != RescueStatus.COMPLETED.value]
    completed = [item for item in overviews if item["status"] == RescueStatus.COMPLETED.value]
    recoveries = 0
    for item in overviews:
        recoveries += len(await store.list_recoveries(UUID(item["id"])))
    return {
        "demo": True,
        "metrics": {
            "active_rescues": len(active),
            "completed_today": len(completed),
            "food_rescued": sum(item["food_quantity"] for item in completed),
            "autonomous_actions": recoveries * 2,
            "human_interventions": len(decisions),
            "recoveries": recoveries,
            "at_risk_rescues": sum(1 for item in active if item["exception_count"]),
        },
        "rescues": overviews,
        "decisions": [item.model_dump(mode="json") for item in decisions],
    }


@router.get("/rescues/{rescue_id}/command-center")
async def rescue_command_center(rescue_id: UUID, request: Request) -> dict[str, Any]:
    database = request.app.state.database
    async with database.session_factory() as session:
        rescue = await session.get(RescueRecord, rescue_id)
        if rescue is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Rescue not found")
        if rescue.donation_id is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Rescue donation is missing")
        donation = await session.get(DonationRecord, rescue.donation_id)
        if donation is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Rescue donation is missing")
        donor = await session.get(DonorRecord, donation.donor_id)
        item_rows = (
            await session.scalars(
                select(FoodItemRecord).where(FoodItemRecord.donation_id == donation.id)
            )
        ).all()
    overview = await _rescue_overview(request, rescue)
    store = cast(NetworkStore, request.app.state.network_store)
    allocations = await store.list_allocations(rescue_id)
    assignments = await store.list_assignments(rescue_id)
    exceptions = await store.list_exceptions(rescue_id)
    recoveries = await store.list_recoveries(rescue_id)
    decisions = await store.list_decisions(rescue_id)
    recipients = {item.id: item for item in await store.list_recipients()}
    drivers = {item.id: item for item in await store.list_drivers()}
    async with SqlAlchemyUnitOfWork(database.session_factory) as uow:
        events = await uow.events.list_for_rescue(rescue_id)
        actions = await uow.agent_actions.list_for_rescue(rescue_id)
    timeline = [
        {
            "kind": event.event_type.value,
            "at": event.timestamp.isoformat(),
            "actor": event.actor.value,
            "detail": event.payload,
            "trace_id": event.trace_id,
        }
        for event in events
    ]
    timeline.extend(
        {
            "kind": action.action_name,
            "at": action.timestamp.isoformat(),
            "actor": "relay",
            "detail": {"summary": action.result_summary or action.decision_reason},
            "trace_id": action.trace_id,
        }
        for action in actions
    )
    timeline.sort(key=lambda item: str(item["at"]))
    return {
        "rescue": overview,
        "donor": donor.name if donor else "Unknown donor",
        "trace_id": events[0].trace_id if events else None,
        "food_items": [
            {
                "name": item.name,
                "quantity": str(item.quantity),
                "unit": item.unit,
                "requires_refrigeration": item.requires_refrigeration,
                "handling_category": item.handling_category,
            }
            for item in item_rows
        ],
        "allocations": [
            {
                "id": str(item.id),
                "recipient": recipients[item.recipient_id].name
                if recipients.get(item.recipient_id) is not None
                else "Unknown",
                "quantity": str(item.quantity),
                "unit": item.unit,
                "status": item.status.value,
            }
            for item in allocations
        ],
        "assignments": [
            {
                "id": str(item.id),
                "driver": drivers[item.driver_id].name
                if drivers.get(item.driver_id) is not None
                else "Unknown",
                "status": item.status.value,
                "created_at": item.created_at.isoformat(),
            }
            for item in assignments
        ],
        "exceptions": [item.model_dump(mode="json") for item in exceptions],
        "recoveries": [item.model_dump(mode="json") for item in recoveries],
        "decisions": [item.model_dump(mode="json") for item in decisions],
        "timeline": timeline,
        "route": {"source": "STATIC / DEMO ROUTE", "pickup_feasible": True},
        "receipt": {
            "verified": rescue.status == RescueStatus.COMPLETED.value,
            "completed_at": _time(rescue.updated_at),
        },
    }


@router.post("/demo/hero")
async def run_demo_hero(request: Request) -> dict[str, Any]:
    if request.app.state.settings.environment == "production":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demo controls are unavailable")
    database = request.app.state.database
    await seed_demo_network(database.session_factory)
    summary = await run_hero_scenario(
        NetworkStore(database.session_factory),
        lambda: SqlAlchemyUnitOfWork(database.session_factory),
    )
    return summary.model_dump(mode="json")
