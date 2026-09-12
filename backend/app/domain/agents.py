from uuid import UUID

from pydantic import AwareDatetime, Field

from app.domain.base import Entity, utc_now
from app.domain.enums import AgentInvocationStatus, CommunicationRequestStatus


class AgentInvocation(Entity):
    rescue_id: UUID | None = None
    agent_name: str = Field(min_length=1, max_length=100)
    invocation_type: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=100)
    model_provider: str = Field(min_length=1, max_length=50)
    model_id: str = Field(min_length=1, max_length=255)
    trace_id: str = Field(min_length=1, max_length=100)
    status: AgentInvocationStatus
    tool_names: tuple[str, ...] = ()
    action_proposed: str | None = Field(default=None, max_length=100)
    result_summary: str = Field(min_length=1, max_length=2000)
    latency_ms: float = Field(ge=0)
    timestamp: AwareDatetime = Field(default_factory=utc_now)


class CommunicationRequest(Entity):
    rescue_id: UUID
    target: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)
    trace_id: str = Field(min_length=1, max_length=100)
    status: CommunicationRequestStatus = CommunicationRequestStatus.QUEUED
    timestamp: AwareDatetime = Field(default_factory=utc_now)
