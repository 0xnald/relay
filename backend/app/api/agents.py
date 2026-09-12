from typing import cast

from fastapi import APIRouter, Request

from app.agents.factory import AgentFactory
from app.schemas.intake import IntakeAgentRequest, IntakeAgentResponse
from app.services.intake import IntakeAgentService

router = APIRouter(prefix="/api/v1/agent", tags=["agent interpretation"])


@router.post("/intake", response_model=IntakeAgentResponse)
async def interpret_intake(body: IntakeAgentRequest, request: Request) -> IntakeAgentResponse:
    factory = cast(AgentFactory, request.app.state.agent_factory)
    return await IntakeAgentService(factory).interpret(
        body.text,
        trace_id=cast(str, request.state.trace_id),
        organization_context=body.organization_context,
        actor_identity=body.actor_identity,
    )
