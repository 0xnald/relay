from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import ConcurrentModification
from app.repositories.sqlalchemy import (
    SqlAlchemyAgentActionRepository,
    SqlAlchemyAgentInvocationRepository,
    SqlAlchemyCommunicationRequestRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyOutboxRepository,
    SqlAlchemyRescueRepository,
    SqlAlchemyToolExecutionRepository,
)


class SqlAlchemyUnitOfWork:
    """One atomic boundary for an event, state mutation, and its audit evidence."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self._committed = False
        self.organizations = SqlAlchemyOrganizationRepository(self._session)
        self.rescues = SqlAlchemyRescueRepository(self._session)
        self.events = SqlAlchemyEventRepository(self._session)
        self.agent_actions = SqlAlchemyAgentActionRepository(self._session)
        self.tool_executions = SqlAlchemyToolExecutionRepository(self._session)
        self.agent_invocations = SqlAlchemyAgentInvocationRepository(self._session)
        self.communication_requests = SqlAlchemyCommunicationRequestRepository(self._session)
        self.outbox = SqlAlchemyOutboxRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None or not self._committed:
            await self._session.rollback()
        await self._session.close()
        self._session = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Unit of work is not active")
        return self._session

    async def flush(self) -> None:
        try:
            await self.session.flush()
        except StaleDataError as exc:
            raise ConcurrentModification() from exc

    async def commit(self) -> None:
        try:
            await self.session.commit()
        except StaleDataError as exc:
            await self.session.rollback()
            raise ConcurrentModification() from exc
        self._committed = True

    async def rollback(self) -> None:
        await self.session.rollback()
