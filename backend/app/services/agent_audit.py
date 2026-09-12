from app.domain.agents import AgentInvocation
from app.services.event_processing import UnitOfWorkFactory


class AgentInvocationAuditService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def record(self, invocation: AgentInvocation) -> None:
        async with self._uow_factory() as uow:
            await uow.agent_invocations.append(invocation)
            await uow.commit()
