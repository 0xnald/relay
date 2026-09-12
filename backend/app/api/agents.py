from typing import cast
from uuid import UUID

from fastapi import APIRouter, Request

from app.agents.factory import AgentFactory
from app.schemas.coordination import CoordinateRescueRequest, CoordinationAgentResponse
from app.schemas.intake import IntakeAgentRequest, IntakeAgentResponse
from app.services.action_execution import AuthorizedActionService
from app.services.agent_audit import AgentInvocationAuditService
from app.services.agent_tools import RelayAgentToolService
from app.services.communications import CommunicationRequestService
from app.services.coordination import CoordinationAgentService
from app.services.event_processing import UnitOfWorkFactory
from app.services.intake import IntakeAgentService

router = APIRouter(prefix="/api/v1/agent", tags=["agent interpretation"])


@router.post("/intake", response_model=IntakeAgentResponse)
async def interpret_intake(body: IntakeAgentRequest, request: Request) -> IntakeAgentResponse:
    factory = cast(AgentFactory, request.app.state.agent_factory)
    unit_of_work = cast(UnitOfWorkFactory, request.app.state.uow_factory)
    return await IntakeAgentService(
        factory, audit_service=AgentInvocationAuditService(unit_of_work)
    ).interpret(
        body.text,
        trace_id=cast(str, request.state.trace_id),
        organization_context=body.organization_context,
        actor_identity=body.actor_identity,
    )


@router.post("/rescues/{rescue_id}/coordinate", response_model=CoordinationAgentResponse)
async def coordinate_rescue(
    rescue_id: UUID, body: CoordinateRescueRequest, request: Request
) -> CoordinationAgentResponse:
    factory = cast(AgentFactory, request.app.state.agent_factory)
    unit_of_work = cast(UnitOfWorkFactory, request.app.state.uow_factory)
    communication_service = CommunicationRequestService(unit_of_work)
    action_service = AuthorizedActionService(unit_of_work)
    tool_service = RelayAgentToolService(
        unit_of_work,
        action_service,
        clarification_handler=communication_service.queue,
    )
    return await CoordinationAgentService(
        factory,
        tool_service,
        audit_service=AgentInvocationAuditService(unit_of_work),
    ).coordinate(
        rescue_id,
        trace_id=cast(str, request.state.trace_id),
        organization_context=body.organization_context,
        actor_identity=body.actor_identity,
    )
