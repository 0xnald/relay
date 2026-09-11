import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import EventStateConflict
from app.domain.enums import ActorRole, EventType, OrganizationType, RescueStatus
from app.domain.events import Event
from app.domain.rescue import Rescue
from app.models.foundational import EventRecord, OrganizationRecord, RescueRecord
from app.repositories.sqlalchemy import SqlAlchemyAgentActionRepository
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.event_processing import EventIngestionService, EventProcessingResult

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    url = os.getenv("RELAY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("RELAY_TEST_DATABASE_URL is required for PostgreSQL integration tests")
    previous = os.getenv("RELAY_DATABASE_URL")
    os.environ["RELAY_DATABASE_URL"] = url
    get_settings.cache_clear()
    configuration = Config("alembic.ini")
    command.upgrade(configuration, "head")
    yield url
    command.downgrade(configuration, "base")
    if previous is None:
        os.environ.pop("RELAY_DATABASE_URL", None)
    else:
        os.environ["RELAY_DATABASE_URL"] = previous
    get_settings.cache_clear()


@pytest.fixture
async def pg_factory(postgres_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE tool_executions, agent_actions, events, rescues, "
                "organizations CASCADE"
            )
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def seed_rescue(factory: async_sessionmaker[AsyncSession], status: RescueStatus) -> Rescue:
    organization_id = uuid4()
    async with factory.begin() as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                name="PostgreSQL Donor",
                kind=OrganizationType.DONOR.value,
            )
        )
    rescue = Rescue(donation_id=uuid4(), status=status)
    async with SqlAlchemyUnitOfWork(factory) as uow:
        persisted = await uow.rescues.create(rescue, donor_organization_id=organization_id)
        await uow.commit()
    return persisted


def coordination_event(
    rescue_id: UUID,
    event_type: EventType,
    key: str,
    *,
    trace_id: str = "trace-postgres",
) -> Event:
    return Event(
        rescue_id=rescue_id,
        actor=ActorRole.SYSTEM,
        event_type=event_type,
        idempotency_key=key,
        trace_id=trace_id,
    )


async def test_migrations_reach_head_and_use_native_postgresql_types(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with pg_factory() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        rows = (
            await session.execute(
                text(
                    "SELECT table_name, column_name, data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE (table_name = 'events' "
                    "AND column_name IN ('id', 'payload', 'created_at')) "
                    "OR (table_name = 'rescues' AND column_name = 'id')"
                )
            )
        ).all()
    types = {(row.table_name, row.column_name): (row.data_type, row.udt_name) for row in rows}

    assert revision == "20260911_0005"
    assert types[("events", "id")][1] == "uuid"
    assert types[("rescues", "id")][1] == "uuid"
    assert types[("events", "payload")][1] == "jsonb"
    assert types[("events", "created_at")][0] == "timestamp with time zone"


async def test_foreign_key_and_idempotency_constraints_are_enforced(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    missing_organization = RescueRecord(
        id=uuid4(),
        donor_organization_id=uuid4(),
        donation_id=uuid4(),
        status=RescueStatus.RECEIVED.value,
        version=1,
    )
    async with pg_factory() as session:
        session.add(missing_organization)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    rescue = await seed_rescue(pg_factory, RescueStatus.RECEIVED)
    first = EventRecord(
        id=uuid4(),
        rescue_id=rescue.id,
        event_type=EventType.DONATION_UPDATED.value,
        actor_role=ActorRole.SYSTEM.value,
        payload={"nested": {"source": "postgres"}},
        idempotency_key="postgres:unique:1",
        trace_id="trace-constraint",
        created_at=datetime.now(UTC),
        actions_created=0,
    )
    duplicate = EventRecord(
        id=uuid4(),
        rescue_id=rescue.id,
        event_type=EventType.DONATION_UPDATED.value,
        actor_role=ActorRole.SYSTEM.value,
        payload={},
        idempotency_key=first.idempotency_key,
        trace_id="trace-constraint",
        created_at=datetime.now(UTC),
        actions_created=0,
    )
    async with pg_factory() as session:
        session.add(first)
        await session.commit()
    async with pg_factory() as session:
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_postgresql_round_trip_preserves_timezone_and_jsonb(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(pg_factory, RescueStatus.RECEIVED)
    event = coordination_event(rescue.id, EventType.DONATION_UPDATED, "postgres:roundtrip:1")
    event = event.model_copy(update={"payload": {"facts": ["one", "two"]}})
    async with SqlAlchemyUnitOfWork(pg_factory) as uow:
        await uow.events.append(event)
        await uow.commit()
    async with SqlAlchemyUnitOfWork(pg_factory) as uow:
        persisted = await uow.events.get_by_idempotency_key(event.idempotency_key)

    assert persisted is not None
    assert persisted.payload == {"facts": ["one", "two"]}
    assert persisted.timestamp.tzinfo is not None
    assert persisted.timestamp.utcoffset() == UTC.utcoffset(persisted.timestamp)


async def test_concurrent_duplicate_event_is_processed_once(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(pg_factory, RescueStatus.DISPATCHED)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(pg_factory))
    first = coordination_event(
        rescue.id, EventType.DRIVER_CANCELLED, "postgres:concurrent-duplicate"
    )
    duplicate = coordination_event(
        rescue.id,
        EventType.DRIVER_CANCELLED,
        first.idempotency_key,
        trace_id="trace-concurrent-retry",
    )

    results = await asyncio.gather(service.process(first), service.process(duplicate))

    assert {result.status for result in results} == {"processed", "replayed"}
    async with SqlAlchemyUnitOfWork(pg_factory) as uow:
        events = await uow.events.list_for_rescue(rescue.id)
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        persisted = await uow.rescues.get(rescue.id)
    assert len(events) == 1
    assert len(actions) == 1
    assert persisted is not None and persisted.status is RescueStatus.EXCEPTION_DETECTED
    assert persisted.version == rescue.version + 1


async def test_concurrent_mutations_do_not_silently_overwrite_state(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(pg_factory, RescueStatus.AWAITING_DRIVER)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(pg_factory))
    first = coordination_event(rescue.id, EventType.DRIVER_ACCEPTED, "postgres:driver:first")
    second = coordination_event(rescue.id, EventType.DRIVER_ACCEPTED, "postgres:driver:second")

    results = await asyncio.gather(
        service.process(first), service.process(second), return_exceptions=True
    )

    assert sum(isinstance(result, EventProcessingResult) for result in results) == 1
    assert sum(isinstance(result, EventStateConflict) for result in results) == 1
    async with SqlAlchemyUnitOfWork(pg_factory) as uow:
        events = await uow.events.list_for_rescue(rescue.id)
        persisted = await uow.rescues.get(rescue.id)
    assert len(events) == 1
    assert persisted is not None and persisted.status is RescueStatus.DISPATCHED
    assert persisted.version == rescue.version + 1


async def test_audit_failure_rolls_back_event_and_state(
    pg_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    rescue = await seed_rescue(pg_factory, RescueStatus.AWAITING_DRIVER)
    service = EventIngestionService(lambda: SqlAlchemyUnitOfWork(pg_factory))
    event = coordination_event(rescue.id, EventType.DRIVER_ACCEPTED, "postgres:audit-failure")

    async def fail_append(repository: SqlAlchemyAgentActionRepository, action: object) -> None:
        raise RuntimeError("injected audit failure")

    monkeypatch.setattr(SqlAlchemyAgentActionRepository, "append", fail_append)
    with pytest.raises(RuntimeError, match="injected audit failure"):
        await service.process(event)

    async with SqlAlchemyUnitOfWork(pg_factory) as uow:
        persisted = await uow.rescues.get(rescue.id)
        stored_event = await uow.events.get_by_idempotency_key(event.idempotency_key)
    assert persisted is not None and persisted.status is RescueStatus.AWAITING_DRIVER
    assert persisted.version == rescue.version
    assert stored_event is None
