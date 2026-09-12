import re
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from strands.types.exceptions import StructuredOutputException

from app.agents.factory import AgentFactory
from app.core.errors import AgentInterpretationFailure
from app.domain.policy import Policy
from app.schemas.coordination import (
    CoordinationAgentResponse,
    CoordinationProposal,
    CoordinationProposalKind,
)
from app.services.agent_tools import RelayAgentToolService
from app.tools.strands import RelayStrandsTools

FABRICATED_CLAIM_PATTERN = re.compile(
    r"\b(food is (?:safe|unsafe)|approved for consumption|recipient accepted|"
    r"driver (?:is )?assigned|delivery (?:is )?confirmed|policy (?:is )?approved)\b",
    re.IGNORECASE,
)


class CoordinationAgentService:
    def __init__(
        self,
        agent_factory: AgentFactory,
        tool_service: RelayAgentToolService,
    ) -> None:
        self._agent_factory = agent_factory
        self._tool_service = tool_service

    async def coordinate(
        self,
        rescue_id: UUID,
        *,
        trace_id: str,
        organization_context: str | None = None,
        actor_identity: str | None = None,
        policy: Policy | None = None,
    ) -> CoordinationAgentResponse:
        strands_tools = RelayStrandsTools()
        agent = self._agent_factory.create_coordination_agent(
            tools=strands_tools.registered(), output_model=CoordinationProposal
        )
        try:
            result = await agent.invoke_async(
                (
                    "Coordinate the rescue for this invocation. Reload current truth with tools, "
                    "evaluate constraints, and return one bounded proposal."
                ),
                invocation_state={
                    "rescue_id": rescue_id,
                    "trace_id": trace_id,
                    "organization_context": organization_context,
                    "actor_identity": actor_identity,
                    "policy": policy,
                    "relay_tool_service": self._tool_service,
                },
                structured_output_model=CoordinationProposal,
            )
            raw: Any = result.structured_output
            proposal = CoordinationProposal.model_validate(raw)
            self._validate_communication(proposal.communication_draft)
        except (StructuredOutputException, ValidationError, ValueError, TypeError) as exc:
            raise AgentInterpretationFailure() from exc

        action_result = None
        clarification_result = None
        if proposal.kind in {
            CoordinationProposalKind.ACTION,
            CoordinationProposalKind.ESCALATION,
        }:
            if proposal.action_type is None:
                raise AgentInterpretationFailure()
            action_result = await self._tool_service.propose_action(
                rescue_id=rescue_id,
                action=proposal.action_type,
                operational_reason=proposal.operational_reason,
                structured_inputs=proposal.structured_inputs,
                trace_id=trace_id,
                agent_name="relay-coordination",
                policy=policy,
            )
        elif proposal.kind is CoordinationProposalKind.CLARIFICATION:
            if proposal.clarification_target is None or proposal.clarification_question is None:
                raise AgentInterpretationFailure()
            clarification_result = await self._tool_service.request_information(
                rescue_id=rescue_id,
                target=proposal.clarification_target,
                question=proposal.clarification_question,
                reason=proposal.operational_reason,
                trace_id=trace_id,
            )
        return CoordinationAgentResponse(
            proposal=proposal,
            action_result=action_result,
            clarification_result=clarification_result,
            trace_id=trace_id,
        )

    @staticmethod
    def _validate_communication(draft: str | None) -> None:
        if draft is not None and FABRICATED_CLAIM_PATTERN.search(draft):
            raise AgentInterpretationFailure()
