import re
import time
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from strands.types.exceptions import StructuredOutputException

from app.agents.factory import AgentFactory
from app.agents.prompts import COORDINATION_PROMPT_VERSION
from app.core.errors import AgentInterpretationFailure
from app.domain.agents import AgentInvocation
from app.domain.enums import AgentInvocationStatus
from app.domain.policy import Policy
from app.observability.agents import InMemoryAgentTelemetry
from app.schemas.coordination import (
    CoordinationAgentResponse,
    CoordinationProposal,
    CoordinationProposalKind,
)
from app.services.agent_audit import AgentInvocationAuditService
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
        audit_service: AgentInvocationAuditService | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._tool_service = tool_service
        self._audit_service = audit_service

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
        started = time.perf_counter()
        telemetry = InMemoryAgentTelemetry()
        agent = self._agent_factory.create_coordination_agent(
            tools=strands_tools.registered(),
            output_model=CoordinationProposal,
            telemetry=telemetry,
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
            await self._record_audit(
                rescue_id=rescue_id,
                trace_id=trace_id,
                status=AgentInvocationStatus.FAILED,
                result_summary="Coordination proposal failed validation.",
                latency_ms=(time.perf_counter() - started) * 1000,
                telemetry=telemetry,
            )
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
        await self._record_audit(
            rescue_id=rescue_id,
            trace_id=trace_id,
            status=AgentInvocationStatus.SUCCEEDED,
            result_summary=f"Coordination proposal: {proposal.kind.value}.",
            latency_ms=(time.perf_counter() - started) * 1000,
            telemetry=telemetry,
            action_proposed=proposal.action_type.value if proposal.action_type else None,
        )
        return CoordinationAgentResponse(
            proposal=proposal,
            action_result=action_result,
            clarification_result=clarification_result,
            trace_id=trace_id,
        )

    async def _record_audit(
        self,
        *,
        rescue_id: UUID,
        trace_id: str,
        status: AgentInvocationStatus,
        result_summary: str,
        latency_ms: float,
        telemetry: InMemoryAgentTelemetry,
        action_proposed: str | None = None,
    ) -> None:
        if self._audit_service is None:
            return
        tool_names = tuple(
            str(attributes["tool_name"])
            for event, attributes in telemetry.events
            if event == "agent_tool_invoked"
        )
        await self._audit_service.record(
            AgentInvocation(
                rescue_id=rescue_id,
                agent_name="relay-coordination",
                invocation_type="rescue_coordination",
                prompt_version=COORDINATION_PROMPT_VERSION,
                model_provider=self._agent_factory.model_provider,
                model_id=self._agent_factory.model_id,
                trace_id=trace_id,
                status=status,
                tool_names=tool_names,
                action_proposed=action_proposed,
                result_summary=result_summary,
                latency_ms=latency_ms,
            )
        )

    @staticmethod
    def _validate_communication(draft: str | None) -> None:
        if draft is not None and FABRICATED_CLAIM_PATTERN.search(draft):
            raise AgentInterpretationFailure()
