from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.errors import ConcurrentModification
from app.domain.audit import AgentAction, ToolExecution
from app.domain.enums import ActionAuthority, OrganizationType, RescueStatus
from app.domain.rescue import Rescue
from app.models import Base
from app.models.foundational import OrganizationRecord
from app.repositories.uow import SqlAlchemyUnitOfWork


@pytest.fixture
async def session_factory(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'repositories.db'}")
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
                name="Community Kitchen",
                kind=OrganizationType.DONOR.value,
            )
        )
    return organization_id


async def create_rescue(factory: async_sessionmaker[AsyncSession], organization_id: UUID) -> Rescue:
    rescue = Rescue(donation_id=uuid4())
    async with SqlAlchemyUnitOfWork(factory) as uow:
        persisted = await uow.rescues.create(rescue, donor_organization_id=organization_id)
        await uow.commit()
    return persisted


async def test_domain_rescue_round_trips_through_repository(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await seed_organization(session_factory)
    persisted = await create_rescue(session_factory, organization_id)

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        loaded = await uow.rescues.get(persisted.id)

    assert loaded == persisted
    assert loaded is not None
    assert loaded.created_at.tzinfo is not None


async def test_unit_of_work_without_commit_rolls_back(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await seed_organization(session_factory)
    rescue = Rescue(donation_id=uuid4())

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.rescues.create(rescue, donor_organization_id=organization_id)

    async with SqlAlchemyUnitOfWork(session_factory) as verification:
        assert await verification.rescues.get(rescue.id) is None


async def test_audit_and_tool_execution_persist_with_trace(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await seed_organization(session_factory)
    rescue = await create_rescue(session_factory, organization_id)
    action = AgentAction(
        rescue_id=rescue.id,
        agent_name="coordination-agent",
        action_name="search_replacement_driver",
        input_summary="Driver cancelled.",
        authority=ActionAuthority.GREEN,
        trace_id="trace-audit",
        permitted=True,
        decision_reason="Routine action is autonomously permitted.",
        succeeded=True,
    )
    execution = ToolExecution(
        rescue_id=rescue.id,
        agent_action_id=action.id,
        agent_name=action.agent_name,
        tool_name="driver_search",
        input_summary="Find eligible drivers.",
        result_summary="Two drivers found.",
        authority=action.authority,
        trace_id=action.trace_id,
        timestamp=datetime.now(UTC),
        succeeded=True,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.agent_actions.append(action)
        await uow.tool_executions.append(execution)
        await uow.commit()

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        executions = await uow.tool_executions.list_for_action(action.id)

    assert actions == [action]
    assert executions == [execution]
    assert executions[0].trace_id == actions[0].trace_id


async def test_optimistic_version_rejects_stale_writer(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    organization_id = await seed_organization(session_factory)
    rescue = await create_rescue(session_factory, organization_id)

    first = SqlAlchemyUnitOfWork(session_factory)
    second = SqlAlchemyUnitOfWork(session_factory)
    async with first, second:
        first_copy = await first.rescues.get(rescue.id)
        stale_copy = await second.rescues.get(rescue.id)
        assert first_copy is not None and stale_copy is not None
        updated = await first.rescues.transition(first_copy, RescueStatus.NORMALIZING)
        await first.commit()

        assert updated.version == rescue.version + 1
        with pytest.raises(ConcurrentModification):
            await second.rescues.transition(stale_copy, RescueStatus.NORMALIZING)
