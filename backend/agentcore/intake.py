"""Narrow AgentCore-compatible Relay Intake Agent entrypoint.

This module has no database or tool access. AgentCore only receives untrusted text
and returns Relay's validated structured intake result.
"""

from uuid import uuid4

from app.agents.factory import AgentFactory
from app.core.config import Settings, get_settings
from app.schemas.agentcore import AgentCoreIntakeRequest, AgentCoreIntakeResponse
from app.services.intake import IntakeAgentService


async def handle_intake(
    request: AgentCoreIntakeRequest, *, settings: Settings | None = None
) -> AgentCoreIntakeResponse:
    active_settings = settings or get_settings()
    trace_id = request.trace_id or f"agentcore-{uuid4()}"
    result = await IntakeAgentService(AgentFactory(active_settings)).interpret(
        request.message,
        trace_id=trace_id,
        actor_identity=request.source,
    )
    return AgentCoreIntakeResponse(result=result, trace_id=trace_id, session_id=request.session_id)
