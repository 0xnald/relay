from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.domain.base import Entity, utc_now
from app.domain.enums import ActionAuthority


class AgentAction(Entity):
    """Auditable action metadata; hidden model reasoning must never be persisted here."""

    rescue_id: UUID
    agent_name: str = Field(min_length=1, max_length=100)
    action_name: str = Field(min_length=1, max_length=100)
    input_summary: str = Field(min_length=1, max_length=2000)
    result_summary: str | None = Field(default=None, max_length=2000)
    authority: ActionAuthority
    policy_reference: str | None = Field(default=None, min_length=1, max_length=255)
    trace_id: str = Field(min_length=1, max_length=100)
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    permitted: bool
    decision_reason: str = Field(min_length=1, max_length=1000)
    succeeded: bool
    error_metadata: dict[str, Any] | None = None


class ToolExecution(Entity):
    rescue_id: UUID
    agent_action_id: UUID
    agent_name: str = Field(min_length=1, max_length=100)
    tool_name: str = Field(min_length=1, max_length=100)
    input_summary: str = Field(min_length=1, max_length=2000)
    result_summary: str | None = Field(default=None, max_length=2000)
    authority: ActionAuthority
    policy_reference: str | None = Field(default=None, min_length=1, max_length=255)
    trace_id: str = Field(min_length=1, max_length=100)
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    succeeded: bool
    error_metadata: dict[str, Any] | None = None
