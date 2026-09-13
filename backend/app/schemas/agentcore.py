from pydantic import Field

from app.schemas.intake import IntakeAgentResponse, IntakeModel


class AgentCoreIntakeRequest(IntakeModel):
    message: str = Field(min_length=1, max_length=10_000)
    source: str = Field(default="agentcore", max_length=100)
    trace_id: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)


class AgentCoreIntakeResponse(IntakeModel):
    status: str = "ok"
    result: IntakeAgentResponse
    agent: str = "relay-intake"
    trace_id: str
    session_id: str | None = None
