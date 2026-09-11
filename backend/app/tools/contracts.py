from typing import Protocol
from uuid import UUID

from pydantic import Field

from app.domain.base import DomainModel
from app.repositories.interfaces import UnitOfWork


class ToolResult(DomainModel):
    summary: str = Field(min_length=1, max_length=2000)


class AuthorizedTool(Protocol):
    """Implemented by application-owned tools, never directly by model output."""

    @property
    def name(self) -> str: ...

    async def execute(self, *, uow: UnitOfWork) -> ToolResult: ...


class GetRescueTool:
    """Read-only foundational tool with no direct session access."""

    name = "get_rescue"

    def __init__(self, rescue_id: UUID) -> None:
        self._rescue_id = rescue_id

    async def execute(self, *, uow: UnitOfWork) -> ToolResult:
        rescue = await uow.rescues.get(self._rescue_id)
        if rescue is None:
            from app.core.errors import RescueNotFound

            raise RescueNotFound()
        return ToolResult(
            summary=f"Rescue is in {rescue.status.value} state at version {rescue.version}."
        )
