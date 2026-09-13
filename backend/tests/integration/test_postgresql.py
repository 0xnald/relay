import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.errors import EventStateConflict
from app.domain.agents import AgentInvocation
from app.domain.enums import (
    ActorRole,
    AgentInvocationStatus,
    AssignmentStatus,
    EventType,
    OrganizationType,
    RescueStatus,
)
from app.domain.events import Event
from app.domain.rescue import Assignment, Donation, FoodItem, Rescue, RescueAllocation
from app.models.foundational import EventRecord, OrganizationRecord, RescueRecord
from app.repositories.network import CapacityUnavailable, NetworkStore
from app.repositories.sqlalchemy import SqlAlchemyAgentActionRepository
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.agent_audit import AgentInvocationAuditService
from app.services.communications import CommunicationRequestService
from app.services.demo_network import (
    HARBOR_ID,
    MARKET_SQUARE_ID,
    MAYA_ID,
    RIVERSIDE_ID,
    seed_demo_network,
)
from app.services.event_processing import EventIngestionService, EventProcessingResult
from app.workflows.hero import run_hero_scenario

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
    truncate = text(
        "TRUNCATE TABLE communication_requests, agent_invocations, tool_executions, "
        "outbox_messages, decision_requests, recovery_attempts, operational_exceptions, "
        "assignments, rescue_allocations, food_items, donations, drivers, recipients, "
        "donors, agent_actions, events, rescues, organizations CASCADE"
    )
    async with engine.begin() as connection:
        await connection.execute(truncate)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as connection:
        await connection.execute(truncate)
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
                    "OR (table_name = 'rescues' AND column_name = 'id') "
                    "OR (table_name = 'agent_invocations' AND column_name = 'tool_names') "
                    "OR (table_name = 'recipients' AND column_name = 'accepted_food_categories') "
                    "OR (table_name = 'decision_requests' AND column_name = 'known_evidence') "
                    "OR (table_name = 'outbox_messages' AND column_name = 'payload')"
                )
            )
        ).all()
    types = {(row.table_name, row.column_name): (row.data_type, row.udt_name) for row in rows}

    assert revision == "20260913_0007"
    assert types[("events", "id")][1] == "uuid"
    assert types[("rescues", "id")][1] == "uuid"
    assert types[("events", "payload")][1] == "jsonb"
    assert types[("agent_invocations", "tool_names")][1] == "jsonb"
    assert types[("recipients", "accepted_food_categories")][1] == "jsonb"
    assert types[("decision_requests", "known_evidence")][1] == "jsonb"
    assert types[("outbox_messages", "payload")][1] == "jsonb"
    assert types[("events", "created_at")][0] == "timestamp with time zone"


async def test_agent_audit_and_communication_requests_round_trip(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(pg_factory, RescueStatus.MATCHING)

    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(pg_factory)

    clarification = await CommunicationRequestService(uow).queue(
        rescue.id,
        "donor",
        "What is the latest pickup time?",
        "Pickup deadline is missing.",
        "trace-agent-postgres",
    )
    await AgentInvocationAuditService(uow).record(
        AgentInvocation(
            rescue_id=rescue.id,
            agent_name="relay-coordination",
            invocation_type="rescue_coordination",
            prompt_version="coordination-v1",
            model_provider="bedrock",
            model_id="global.anthropic.claude-sonnet-4-6",
            trace_id="trace-agent-postgres",
            status=AgentInvocationStatus.SUCCEEDED,
            tool_names=("get_rescue", "request_information"),
            action_proposed=None,
            result_summary="Coordination proposal: clarification.",
            latency_ms=12.5,
        )
    )

    async with uow() as work:
        requests = await work.communication_requests.list_for_rescue(rescue.id)
        invocations = await work.agent_invocations.list_for_rescue(rescue.id)

    assert clarification.status == "queued"
    assert not clarification.delivery_claimed
    assert requests[0].trace_id == "trace-agent-postgres"
    assert invocations[0].tool_names == ("get_rescue", "request_information")
    assert invocations[0].status is AgentInvocationStatus.SUCCEEDED


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


async def seed_network_allocation(
    factory: async_sessionmaker[AsyncSession],
    *,
    quantity: Decimal,
    reserve: bool = False,
) -> tuple[NetworkStore, Rescue, FoodItem, RescueAllocation]:
    await seed_demo_network(factory)
    store = NetworkStore(factory)
    donor = await store.get_donor(MARKET_SQUARE_ID)
    assert donor is not None
    donation = Donation(
        donor_id=donor.id,
        pickup_window_start=datetime.now(UTC),
        pickup_window_end=datetime.now(UTC) + timedelta(hours=3),
    )
    item = FoodItem(
        donation_id=donation.id,
        name="PostgreSQL prepared meals",
        quantity=quantity,
        unit="meals",
        handling_category="prepared_meal",
        requires_refrigeration=True,
        dietary_tags=frozenset({"general"}),
    )
    await store.create_donation(donation, [item])
    rescue = Rescue(donation_id=donation.id)
    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.rescues.create(rescue, donor_organization_id=donor.organization_id)
        await uow.commit()
    allocation = RescueAllocation(
        rescue_id=rescue.id,
        recipient_id=HARBOR_ID,
        food_item_id=item.id,
        quantity=quantity,
        unit=item.unit,
        trace_id="trace-postgres-network",
    )
    if reserve:
        allocation = (await store.reserve_allocations([allocation]))[0]
    return store, rescue, item, allocation


async def test_capacity_row_lock_prevents_concurrent_overbooking(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    first_store, _, _, first = await seed_network_allocation(pg_factory, quantity=Decimal("40"))
    second_store, _, _, second = await seed_network_allocation(pg_factory, quantity=Decimal("40"))

    results = await asyncio.gather(
        first_store.reserve_allocations([first]),
        second_store.reserve_allocations([second]),
        return_exceptions=True,
    )

    assert sum(isinstance(result, list) for result in results) == 1
    assert sum(isinstance(result, CapacityUnavailable) for result in results) == 1
    harbor = next(item for item in await first_store.list_recipients() if item.id == HARBOR_ID)
    assert harbor.available_capacity == 20


async def test_driver_row_lock_prevents_double_assignment(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, rescue, _, allocation = await seed_network_allocation(
        pg_factory, quantity=Decimal("20"), reserve=True
    )
    proposed = [
        Assignment(
            rescue_id=rescue.id,
            allocation_id=allocation.id,
            recipient_id=HARBOR_ID,
            driver_id=MAYA_ID,
            trace_id=f"trace-driver-race-{index}",
        )
        for index in range(2)
    ]

    results = await asyncio.gather(
        *(store.create_assignment(item) for item in proposed), return_exceptions=True
    )

    assert sum(isinstance(result, Assignment) for result in results) == 1
    assert sum(isinstance(result, CapacityUnavailable) for result in results) == 1
    persisted = await store.list_assignments(rescue.id)
    assert len(persisted) == 1
    assert persisted[0].status is AssignmentStatus.RESERVED


async def test_failed_recovery_reassignment_rolls_back_capacity_and_allocation(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    store, rescue, item, original = await seed_network_allocation(
        pg_factory, quantity=Decimal("50"), reserve=True
    )
    replacement = RescueAllocation(
        rescue_id=rescue.id,
        recipient_id=RIVERSIDE_ID,
        food_item_id=item.id,
        quantity=Decimal("50"),
        unit=item.unit,
        trace_id="trace-recovery-rollback",
    )

    with pytest.raises(CapacityUnavailable, match="capacity is insufficient"):
        await store.reassign_allocation(original.id, replacement)

    allocations = await store.list_allocations(rescue.id)
    recipients = {item.id: item for item in await store.list_recipients()}
    assert [(item.id, item.status) for item in allocations] == [
        (original.id, AssignmentStatus.RESERVED)
    ]
    assert recipients[HARBOR_ID].available_capacity == 10
    assert recipients[RIVERSIDE_ID].available_capacity == 45


async def test_hero_path_persists_decision_recovery_and_outbox(
    pg_factory: async_sessionmaker[AsyncSession],
) -> None:
    await seed_demo_network(pg_factory)
    store = NetworkStore(pg_factory)
    summary = await run_hero_scenario(store, lambda: SqlAlchemyUnitOfWork(pg_factory))
    decisions = await store.list_decisions()
    outbox = await store.list_outbox()

    assert summary.final_rescue_status == "completed"
    assert summary.delivery_verified
    assert len(decisions) == 1 and decisions[0].status.value == "resolved"
    assert {item.message_type for item in outbox} >= {
        "recipient_assigned",
        "driver_assigned",
        "assignment_changed",
    }
