from collections.abc import Sequence
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.domain.audit import AgentAction, ToolExecution
from app.domain.enums import RescueStatus
from app.domain.events import Event
from app.domain.rescue import Rescue


class RescueRepository(Protocol):
    async def get(self, rescue_id: UUID) -> Rescue | None: ...

    async def create(self, rescue: Rescue, *, donor_organization_id: UUID) -> Rescue: ...

    async def save(self, rescue: Rescue) -> Rescue: ...

    async def transition(self, rescue: Rescue, target: RescueStatus) -> Rescue: ...

    async def lock_for_update(self, rescue_id: UUID) -> Rescue | None: ...


class EventRepository(Protocol):
    async def get_by_idempotency_key(self, key: str) -> Event | None: ...

    async def append(self, event: Event) -> Event: ...

    async def list_for_rescue(self, rescue_id: UUID) -> Sequence[Event]: ...


class AgentActionRepository(Protocol):
    async def append(self, action: AgentAction) -> AgentAction: ...

    async def list_for_rescue(self, rescue_id: UUID) -> Sequence[AgentAction]: ...


class ToolExecutionRepository(Protocol):
    async def append(self, execution: ToolExecution) -> ToolExecution: ...

    async def list_for_action(self, action_id: UUID) -> Sequence[ToolExecution]: ...

    async def list_for_rescue(self, rescue_id: UUID) -> Sequence[ToolExecution]: ...


class UnitOfWork(Protocol):
    rescues: RescueRepository
    events: EventRepository
    agent_actions: AgentActionRepository
    tool_executions: ToolExecutionRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
