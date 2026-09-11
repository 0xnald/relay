from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import DuplicateEventConflict, EventStateConflict, UnsupportedEvent
from app.domain.enums import ActorRole, EventType, OrganizationType, RescueStatus
from app.domain.events import Event
from app.domain.rescue import Rescue
from app.models import Base
from app.models.foundational import OrganizationRecord
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.event_processing import EventIngestionService


@pytest.fixture
async def event_session_factory(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'events.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def seed_organization(factory: async_sessionmaker[AsyncSession]) -> UUID:
    organization_id = uuid4()
    async with factory.begin() as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                name="Rescue Donor",
                kind=OrganizationType.DONOR.value,
            )
        )
    return organization_id


async def seed_rescue(factory: async_sessionmaker[AsyncSession], status: RescueStatus) -> Rescue:
    organization_id = await seed_organization(factory)
    rescue = Rescue(donation_id=uuid4(), status=status)
    async with SqlAlchemyUnitOfWork(factory) as uow:
        persisted = await uow.rescues.create(rescue, donor_organization_id=organization_id)
        await uow.commit()
    return persisted


def event_for(
    rescue_id: UUID,
    event_type: EventType,
    *,
    key: str,
    payload: dict[str, object] | None = None,
    trace_id: str = "trace-event",
) -> Event:
    return Event(
        rescue_id=rescue_id,
        actor=ActorRole.SYSTEM,
        event_type=event_type,
        payload=payload or {},
        idempotency_key=key,
        trace_id=trace_id,
    )


async def test_donation_created_initializes_rescue_atomically(
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await seed_organization(event_session_factory)
    rescue_id = uuid4()
    event = event_for(
        rescue_id,
        EventType.DONATION_CREATED,
        key="donation:new",
        payload={"donation_id": str(uuid4()), "donor_organization_id": str(organization_id)},
    )
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))

    result = await service.process(event)

    assert result.rescue_status_before is None
    assert result.rescue_status_after is RescueStatus.RECEIVED
    assert result.actions_created == 1
    async with SqlAlchemyUnitOfWork(event_session_factory) as uow:
        assert await uow.rescues.get(rescue_id) is not None
        assert len(await uow.events.list_for_rescue(rescue_id)) == 1
        assert len(await uow.agent_actions.list_for_rescue(rescue_id)) == 1


async def test_same_event_is_an_idempotent_replay(
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(event_session_factory, RescueStatus.AWAITING_DRIVER)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))
    first_event = event_for(rescue.id, EventType.DRIVER_ACCEPTED, key="driver:accepted:1")
    replay = event_for(
        rescue.id,
        EventType.DRIVER_ACCEPTED,
        key="driver:accepted:1",
        trace_id="trace-retry",
    )

    first = await service.process(first_event)
    second = await service.process(replay)

    assert first.rescue_status_after is RescueStatus.DISPATCHED
    assert second.event_id == first.event_id
    assert second.idempotent_replay
    assert second.status == "replayed"
    assert second.actions_created == 0
    assert second.trace_id == "trace-retry"


async def test_same_key_with_conflicting_payload_is_rejected(
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(event_session_factory, RescueStatus.AWAITING_RECIPIENT)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))
    await service.process(
        event_for(rescue.id, EventType.RECIPIENT_ACCEPTED, key="recipient:response:1")
    )

    with pytest.raises(DuplicateEventConflict):
        await service.process(
            event_for(
                rescue.id,
                EventType.RECIPIENT_ACCEPTED,
                key="recipient:response:1",
                payload={"capacity": 10},
            )
        )


@pytest.mark.parametrize(
    ("initial", "event_type", "expected"),
    [
        (RescueStatus.AWAITING_RECIPIENT, EventType.RECIPIENT_ACCEPTED, RescueStatus.ASSIGNED),
        (RescueStatus.AWAITING_RECIPIENT, EventType.RECIPIENT_DECLINED, RescueStatus.MATCHING),
        (RescueStatus.AWAITING_DRIVER, EventType.DRIVER_ACCEPTED, RescueStatus.DISPATCHED),
        (RescueStatus.DISPATCHED, EventType.DRIVER_CANCELLED, RescueStatus.EXCEPTION_DETECTED),
        (RescueStatus.PICKUP_PENDING, EventType.PICKUP_CONFIRMED, RescueStatus.IN_TRANSIT),
        (RescueStatus.DELIVERY_PENDING, EventType.DELIVERY_CONFIRMED, RescueStatus.VERIFYING),
        (RescueStatus.VERIFYING, EventType.DELIVERY_MISMATCH, RescueStatus.EXCEPTION_DETECTED),
        (RescueStatus.HUMAN_REVIEW, EventType.HUMAN_DECISION_RECEIVED, RescueStatus.RESOLVED),
    ],
)
async def test_deterministic_event_transitions(
    event_session_factory: async_sessionmaker[AsyncSession],
    initial: RescueStatus,
    event_type: EventType,
    expected: RescueStatus,
) -> None:
    rescue = await seed_rescue(event_session_factory, initial)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))

    result = await service.process(
        event_for(
            rescue.id,
            event_type,
            key=f"event:{event_type.value}:{rescue.id}",
            payload={"target_status": RescueStatus.COMPLETED.value},
        )
    )

    assert result.rescue_status_before is initial
    assert result.rescue_status_after is expected


async def test_invalid_event_state_rolls_back_event(
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(event_session_factory, RescueStatus.RECEIVED)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))
    event = event_for(rescue.id, EventType.DELIVERY_CONFIRMED, key="delivery:too-early")

    with pytest.raises(EventStateConflict):
        await service.process(event)

    async with SqlAlchemyUnitOfWork(event_session_factory) as uow:
        assert await uow.events.get_by_idempotency_key(event.idempotency_key) is None


async def test_unsupported_event_fails_without_persistence(
    event_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(event_session_factory, RescueStatus.RECEIVED)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))
    event = event_for(rescue.id, EventType.DONATION_UPDATED, key="donation:update:1")

    with pytest.raises(UnsupportedEvent):
        await service.process(event)

    async with SqlAlchemyUnitOfWork(event_session_factory) as uow:
        assert await uow.events.get_by_idempotency_key(event.idempotency_key) is None


@pytest.mark.parametrize(
    ("initial", "event_type"),
    [
        (RescueStatus.DISPATCHED, EventType.DRIVER_CANCELLED),
        (RescueStatus.DELIVERY_PENDING, EventType.DELIVERY_CONFIRMED),
    ],
)
async def test_replayed_events_do_not_duplicate_progress_or_audit(
    event_session_factory: async_sessionmaker[AsyncSession],
    initial: RescueStatus,
    event_type: EventType,
) -> None:
    rescue = await seed_rescue(event_session_factory, initial)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(event_session_factory))
    first = event_for(rescue.id, event_type, key=f"replay:{event_type.value}")
    replay = event_for(rescue.id, event_type, key=first.idempotency_key)

    outcome = await service.process(first)
    repeated = await service.process(replay)

    assert repeated.rescue_status_after is outcome.rescue_status_after
    async with SqlAlchemyUnitOfWork(event_session_factory) as uow:
        events = await uow.events.list_for_rescue(rescue.id)
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        persisted = await uow.rescues.get(rescue.id)
    assert len(events) == 1
    assert len(actions) == 1
    assert persisted is not None and persisted.version == rescue.version + 1
