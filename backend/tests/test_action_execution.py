from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.enums import ActionAuthority, ActionType, OrganizationType, RescueStatus
from app.domain.policy import Policy
from app.domain.rescue import Rescue
from app.models import Base
from app.models.foundational import OrganizationRecord
from app.repositories.interfaces import UnitOfWork
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.services.action_execution import AuthorizedActionService, ProposedAction
from app.tools.contracts import ToolResult


@pytest.fixture
async def action_session_factory(
    tmp_path: Path,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'actions.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def seed_rescue(factory: async_sessionmaker[AsyncSession]) -> Rescue:
    organization_id = uuid4()
    async with factory.begin() as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                name="Action Donor",
                kind=OrganizationType.DONOR.value,
            )
        )
    rescue = Rescue(donation_id=uuid4())
    async with SqlAlchemyUnitOfWork(factory) as uow:
        persisted = await uow.rescues.create(rescue, donor_organization_id=organization_id)
        await uow.commit()
    return persisted


class CountingTool:
    name = "counting_tool"

    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, *, uow: UnitOfWork) -> ToolResult:
        self.calls += 1
        return ToolResult(summary="Tool completed.")


class MutatingFailureTool:
    name = "mutating_failure_tool"

    def __init__(self, rescue_id: UUID) -> None:
        self.rescue_id = rescue_id

    async def execute(self, *, uow: UnitOfWork) -> ToolResult:
        rescue = await uow.rescues.lock_for_update(self.rescue_id)
        assert rescue is not None
        await uow.rescues.transition(rescue, RescueStatus.NORMALIZING)
        raise RuntimeError("simulated tool failure")


def proposal(rescue_id: UUID, action: ActionType) -> ProposedAction:
    return ProposedAction(
        rescue_id=rescue_id,
        action=action,
        agent_name="future-coordination-agent",
        input_summary="Operational action proposed from typed facts.",
        trace_id="trace-action",
    )


async def test_green_action_executes_without_policy_reference(
    action_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(action_session_factory)
    tool = CountingTool()
    service = AuthorizedActionService(lambda: SqlAlchemyUnitOfWork(action_session_factory))

    result = await service.execute(proposal(rescue.id, ActionType.SEND_STATUS_UPDATE), tool)

    assert result.succeeded
    assert result.policy_reference is None
    assert tool.calls == 1
    async with SqlAlchemyUnitOfWork(action_session_factory) as uow:
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        executions = await uow.tool_executions.list_for_rescue(rescue.id)
    assert actions[0].policy_reference is None
    assert executions[0].agent_action_id == actions[0].id


async def test_amber_action_executes_only_under_explicit_policy(
    action_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(action_session_factory)
    tool = CountingTool()
    policy = Policy(
        name="Split policy",
        reference="split-v2",
        allowed_amber_actions=frozenset({ActionType.SPLIT_RESCUE}),
    )
    service = AuthorizedActionService(lambda: SqlAlchemyUnitOfWork(action_session_factory))

    result = await service.execute(
        proposal(rescue.id, ActionType.SPLIT_RESCUE), tool, policy=policy
    )

    assert result.succeeded
    assert result.authority is ActionAuthority.AMBER
    assert result.policy_reference == "split-v2"
    assert tool.calls == 1


async def test_amber_without_policy_is_denied_and_audited(
    action_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(action_session_factory)
    tool = CountingTool()
    service = AuthorizedActionService(lambda: SqlAlchemyUnitOfWork(action_session_factory))

    result = await service.execute(proposal(rescue.id, ActionType.SPLIT_RESCUE), tool)

    assert result.status == "denied"
    assert result.requires_human
    assert tool.calls == 0
    async with SqlAlchemyUnitOfWork(action_session_factory) as uow:
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        executions = await uow.tool_executions.list_for_rescue(rescue.id)
    assert len(actions) == 1 and not actions[0].permitted
    assert executions == []


async def test_red_action_escalates_without_invoking_tool(
    action_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(action_session_factory)
    tool = CountingTool()
    policy = Policy(name="Handling rules", reference="handling-v3")
    service = AuthorizedActionService(lambda: SqlAlchemyUnitOfWork(action_session_factory))

    result = await service.execute(
        proposal(rescue.id, ActionType.CONTINUE_WITH_MISSING_EVIDENCE),
        tool,
        policy=policy,
    )

    assert result.status == "escalated"
    assert result.policy_reference == "handling-v3"
    assert result.requires_human
    assert tool.calls == 0


async def test_tool_failure_rolls_back_mutation_and_persists_safe_failure_audit(
    action_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    rescue = await seed_rescue(action_session_factory)
    service = AuthorizedActionService(lambda: SqlAlchemyUnitOfWork(action_session_factory))

    result = await service.execute(
        proposal(rescue.id, ActionType.SEND_STATUS_UPDATE), MutatingFailureTool(rescue.id)
    )

    assert result.status == "failed"
    async with SqlAlchemyUnitOfWork(action_session_factory) as uow:
        persisted = await uow.rescues.get(rescue.id)
        actions = await uow.agent_actions.list_for_rescue(rescue.id)
        executions = await uow.tool_executions.list_for_rescue(rescue.id)
    assert persisted is not None and persisted.status is RescueStatus.RECEIVED
    assert len(actions) == 1 and not actions[0].succeeded
    assert actions[0].error_metadata == {
        "code": "tool_execution_failed",
        "error_type": "RuntimeError",
    }
    assert len(executions) == 1 and not executions[0].succeeded
