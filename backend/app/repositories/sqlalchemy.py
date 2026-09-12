from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConcurrentModification, RescueNotFound
from app.domain.agents import AgentInvocation, CommunicationRequest
from app.domain.audit import AgentAction, ToolExecution
from app.domain.enums import (
    ActionAuthority,
    ActorRole,
    AgentInvocationStatus,
    CommunicationRequestStatus,
    EventType,
    RescueStatus,
)
from app.domain.events import Event, EventOutcome
from app.domain.rescue import Rescue
from app.models.foundational import (
    AgentActionRecord,
    AgentInvocationRecord,
    CommunicationRequestRecord,
    EventRecord,
    OrganizationRecord,
    RescueRecord,
    ToolExecutionRecord,
)
from app.services.state_machine import transition


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def rescue_to_domain(record: RescueRecord) -> Rescue:
    if record.donation_id is None:
        raise ValueError("Persisted rescue has no donation identifier")
    return Rescue(
        id=record.id,
        donation_id=record.donation_id,
        status=RescueStatus(record.status),
        version=record.version,
        created_at=_utc(record.created_at),
        updated_at=_utc(record.updated_at),
    )


def event_to_domain(record: EventRecord) -> Event:
    return Event(
        id=record.id,
        rescue_id=record.rescue_id,
        actor=ActorRole(record.actor_role),
        actor_id=record.actor_id,
        timestamp=_utc(record.created_at),
        event_type=EventType(record.event_type),
        payload=record.payload,
        idempotency_key=record.idempotency_key,
        trace_id=record.trace_id,
    )


def action_to_domain(record: AgentActionRecord) -> AgentAction:
    return AgentAction(
        id=record.id,
        rescue_id=record.rescue_id,
        agent_name=record.agent_name,
        action_name=record.action_name,
        input_summary=record.input_summary,
        result_summary=record.result_summary,
        authority=ActionAuthority(record.authority),
        policy_reference=record.policy_reference,
        trace_id=record.trace_id,
        timestamp=_utc(record.occurred_at),
        permitted=record.permitted,
        decision_reason=record.decision_reason,
        succeeded=record.succeeded,
        error_metadata=record.error_metadata,
    )


def tool_execution_to_domain(record: ToolExecutionRecord) -> ToolExecution:
    return ToolExecution(
        id=record.id,
        rescue_id=record.rescue_id,
        agent_action_id=record.agent_action_id,
        agent_name=record.agent_name,
        tool_name=record.tool_name,
        input_summary=record.input_summary,
        result_summary=record.result_summary,
        authority=ActionAuthority(record.authority),
        policy_reference=record.policy_reference,
        trace_id=record.trace_id,
        timestamp=_utc(record.occurred_at),
        succeeded=record.succeeded,
        error_metadata=record.error_metadata,
    )


def agent_invocation_to_domain(record: AgentInvocationRecord) -> AgentInvocation:
    return AgentInvocation(
        id=record.id,
        rescue_id=record.rescue_id,
        agent_name=record.agent_name,
        invocation_type=record.invocation_type,
        prompt_version=record.prompt_version,
        model_provider=record.model_provider,
        model_id=record.model_id,
        trace_id=record.trace_id,
        status=AgentInvocationStatus(record.status),
        tool_names=tuple(record.tool_names),
        action_proposed=record.action_proposed,
        result_summary=record.result_summary,
        latency_ms=record.latency_ms,
        timestamp=_utc(record.occurred_at),
    )


def communication_request_to_domain(
    record: CommunicationRequestRecord,
) -> CommunicationRequest:
    return CommunicationRequest(
        id=record.id,
        rescue_id=record.rescue_id,
        target=record.target,
        question=record.question,
        reason=record.reason,
        trace_id=record.trace_id,
        status=CommunicationRequestStatus(record.status),
        timestamp=_utc(record.occurred_at),
    )


class SqlAlchemyRescueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, rescue_id: UUID) -> Rescue | None:
        record = await self._session.get(RescueRecord, rescue_id)
        return rescue_to_domain(record) if record is not None else None

    async def create(self, rescue: Rescue, *, donor_organization_id: UUID) -> Rescue:
        record = RescueRecord(
            id=rescue.id,
            donor_organization_id=donor_organization_id,
            donation_id=rescue.donation_id,
            status=rescue.status.value,
            version=rescue.version,
            created_at=rescue.created_at,
            updated_at=rescue.updated_at,
        )
        self._session.add(record)
        await self._session.flush()
        return rescue_to_domain(record)

    async def save(self, rescue: Rescue) -> Rescue:
        record = await self._session.get(RescueRecord, rescue.id)
        if record is None:
            raise RescueNotFound()
        if record.version != rescue.version:
            raise ConcurrentModification()
        record.status = rescue.status.value
        try:
            await self._session.flush()
        except StaleDataError as exc:
            raise ConcurrentModification() from exc
        await self._session.refresh(record)
        return rescue_to_domain(record)

    async def transition(self, rescue: Rescue, target: RescueStatus) -> Rescue:
        next_status = transition(rescue.status, target)
        return await self.save(rescue.model_copy(update={"status": next_status}))

    async def lock_for_update(self, rescue_id: UUID) -> Rescue | None:
        statement = select(RescueRecord).where(RescueRecord.id == rescue_id).with_for_update()
        record = await self._session.scalar(statement)
        return rescue_to_domain(record) if record is not None else None


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, organization_id: UUID) -> bool:
        return (
            await self._session.scalar(
                select(OrganizationRecord.id).where(OrganizationRecord.id == organization_id)
            )
            is not None
        )


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_idempotency_key(self, key: str) -> Event | None:
        record = await self._session.scalar(
            select(EventRecord).where(EventRecord.idempotency_key == key)
        )
        return event_to_domain(record) if record is not None else None

    async def append(self, event: Event) -> Event:
        record = EventRecord(
            id=event.id,
            rescue_id=event.rescue_id,
            event_type=event.event_type.value,
            actor_role=event.actor.value,
            actor_id=event.actor_id,
            payload=event.payload,
            idempotency_key=event.idempotency_key,
            trace_id=event.trace_id,
            created_at=event.timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return event_to_domain(record)

    async def list_for_rescue(self, rescue_id: UUID) -> list[Event]:
        records = (
            await self._session.scalars(
                select(EventRecord)
                .where(EventRecord.rescue_id == rescue_id)
                .order_by(EventRecord.created_at, EventRecord.id)
            )
        ).all()
        return [event_to_domain(record) for record in records]

    async def set_outcome(self, event_id: UUID, outcome: EventOutcome) -> None:
        record = await self._session.get(EventRecord, event_id)
        if record is None:
            raise ValueError("Cannot record an outcome for a missing event")
        record.rescue_status_before = (
            outcome.rescue_status_before.value if outcome.rescue_status_before else None
        )
        record.rescue_status_after = outcome.rescue_status_after.value
        record.actions_created = outcome.actions_created
        await self._session.flush()

    async def get_outcome(self, event_id: UUID) -> EventOutcome | None:
        record = await self._session.get(EventRecord, event_id)
        if record is None or record.rescue_status_after is None:
            return None
        return EventOutcome(
            rescue_status_before=(
                RescueStatus(record.rescue_status_before)
                if record.rescue_status_before is not None
                else None
            ),
            rescue_status_after=RescueStatus(record.rescue_status_after),
            actions_created=record.actions_created,
        )


class SqlAlchemyAgentActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, action: AgentAction) -> AgentAction:
        record = AgentActionRecord(
            id=action.id,
            rescue_id=action.rescue_id,
            agent_name=action.agent_name,
            action_name=action.action_name,
            input_summary=action.input_summary,
            result_summary=action.result_summary,
            authority=action.authority.value,
            policy_reference=action.policy_reference,
            trace_id=action.trace_id,
            occurred_at=action.timestamp,
            permitted=action.permitted,
            decision_reason=action.decision_reason,
            succeeded=action.succeeded,
            error_metadata=action.error_metadata,
        )
        self._session.add(record)
        await self._session.flush()
        return action_to_domain(record)

    async def list_for_rescue(self, rescue_id: UUID) -> list[AgentAction]:
        records = (
            await self._session.scalars(
                select(AgentActionRecord)
                .where(AgentActionRecord.rescue_id == rescue_id)
                .order_by(AgentActionRecord.occurred_at, AgentActionRecord.id)
            )
        ).all()
        return [action_to_domain(record) for record in records]


class SqlAlchemyToolExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, execution: ToolExecution) -> ToolExecution:
        record = ToolExecutionRecord(
            id=execution.id,
            rescue_id=execution.rescue_id,
            agent_action_id=execution.agent_action_id,
            agent_name=execution.agent_name,
            tool_name=execution.tool_name,
            input_summary=execution.input_summary,
            result_summary=execution.result_summary,
            authority=execution.authority.value,
            policy_reference=execution.policy_reference,
            trace_id=execution.trace_id,
            occurred_at=execution.timestamp,
            succeeded=execution.succeeded,
            error_metadata=execution.error_metadata,
        )
        self._session.add(record)
        await self._session.flush()
        return tool_execution_to_domain(record)

    async def list_for_action(self, action_id: UUID) -> list[ToolExecution]:
        records = (
            await self._session.scalars(
                select(ToolExecutionRecord)
                .where(ToolExecutionRecord.agent_action_id == action_id)
                .order_by(ToolExecutionRecord.occurred_at, ToolExecutionRecord.id)
            )
        ).all()
        return [tool_execution_to_domain(record) for record in records]

    async def list_for_rescue(self, rescue_id: UUID) -> list[ToolExecution]:
        records = (
            await self._session.scalars(
                select(ToolExecutionRecord)
                .where(ToolExecutionRecord.rescue_id == rescue_id)
                .order_by(ToolExecutionRecord.occurred_at, ToolExecutionRecord.id)
            )
        ).all()
        return [tool_execution_to_domain(record) for record in records]


class SqlAlchemyAgentInvocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, invocation: AgentInvocation) -> AgentInvocation:
        record = AgentInvocationRecord(
            id=invocation.id,
            rescue_id=invocation.rescue_id,
            agent_name=invocation.agent_name,
            invocation_type=invocation.invocation_type,
            prompt_version=invocation.prompt_version,
            model_provider=invocation.model_provider,
            model_id=invocation.model_id,
            trace_id=invocation.trace_id,
            status=invocation.status.value,
            tool_names=list(invocation.tool_names),
            action_proposed=invocation.action_proposed,
            result_summary=invocation.result_summary,
            latency_ms=invocation.latency_ms,
            occurred_at=invocation.timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return agent_invocation_to_domain(record)

    async def list_for_rescue(self, rescue_id: UUID) -> list[AgentInvocation]:
        records = (
            await self._session.scalars(
                select(AgentInvocationRecord)
                .where(AgentInvocationRecord.rescue_id == rescue_id)
                .order_by(AgentInvocationRecord.occurred_at, AgentInvocationRecord.id)
            )
        ).all()
        return [agent_invocation_to_domain(record) for record in records]


class SqlAlchemyCommunicationRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, request: CommunicationRequest) -> CommunicationRequest:
        record = CommunicationRequestRecord(
            id=request.id,
            rescue_id=request.rescue_id,
            target=request.target,
            question=request.question,
            reason=request.reason,
            trace_id=request.trace_id,
            status=request.status.value,
            occurred_at=request.timestamp,
        )
        self._session.add(record)
        await self._session.flush()
        return communication_request_to_domain(record)

    async def list_for_rescue(self, rescue_id: UUID) -> list[CommunicationRequest]:
        records = (
            await self._session.scalars(
                select(CommunicationRequestRecord)
                .where(CommunicationRequestRecord.rescue_id == rescue_id)
                .order_by(
                    CommunicationRequestRecord.occurred_at,
                    CommunicationRequestRecord.id,
                )
            )
        ).all()
        return [communication_request_to_domain(record) for record in records]
