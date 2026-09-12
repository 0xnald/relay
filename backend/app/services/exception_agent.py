import time
from typing import Any

from app.agents.factory import AgentFactory
from app.agents.prompts import EXCEPTION_PROMPT_VERSION
from app.core.errors import AgentInterpretationFailure
from app.domain.agents import AgentInvocation
from app.domain.enums import AgentInvocationStatus
from app.domain.network import OperationalException
from app.observability.agents import InMemoryAgentTelemetry
from app.schemas.recovery import RecoveryProposal
from app.services.agent_audit import AgentInvocationAuditService
from app.services.recovery import RecoveryOption


class ExceptionAgentService:
    def __init__(
        self,
        factory: AgentFactory,
        audit: AgentInvocationAuditService | None = None,
    ) -> None:
        self.factory = factory
        self.audit = audit

    async def choose(
        self,
        exception: OperationalException,
        options: tuple[RecoveryOption, ...],
        *,
        trace_id: str,
    ) -> RecoveryProposal:
        if len(options) < 2:
            raise ValueError("exception agent is only used when multiple strategies exist")
        started = time.perf_counter()
        telemetry = InMemoryAgentTelemetry()
        agent = self.factory.create_exception_agent(RecoveryProposal, telemetry=telemetry)
        prompt = (
            f"EXCEPTION_DATA\n{exception.model_dump_json()}\nEND_EXCEPTION_DATA\n\n"
            "CANDIDATE_STRATEGIES\n"
            + "\n".join(option.model_dump_json() for option in options)
            + "\nEND_CANDIDATE_STRATEGIES"
        )
        try:
            result = await agent.invoke_async(
                prompt,
                invocation_state={"trace_id": trace_id, "rescue_id": exception.rescue_id},
                structured_output_model=RecoveryProposal,
            )
            raw: Any = result.structured_output
            proposal = RecoveryProposal.model_validate(raw)
            permitted = {option.strategy for option in options}
            if proposal.strategy not in permitted:
                raise ValueError("agent selected a strategy outside the deterministic options")
        except Exception as exc:
            await self._record(
                exception,
                trace_id,
                AgentInvocationStatus.FAILED,
                "Exception strategy proposal failed validation.",
                (time.perf_counter() - started) * 1000,
            )
            raise AgentInterpretationFailure() from exc
        await self._record(
            exception,
            trace_id,
            AgentInvocationStatus.SUCCEEDED,
            f"Selected permitted strategy: {proposal.strategy.value}.",
            (time.perf_counter() - started) * 1000,
        )
        return proposal

    async def _record(
        self,
        exception: OperationalException,
        trace_id: str,
        status: AgentInvocationStatus,
        summary: str,
        latency_ms: float,
    ) -> None:
        if self.audit is None:
            return
        await self.audit.record(
            AgentInvocation(
                rescue_id=exception.rescue_id,
                agent_name="relay-exception",
                invocation_type="exception_strategy_selection",
                prompt_version=EXCEPTION_PROMPT_VERSION,
                model_provider=self.factory.model_provider,
                model_id=self.factory.model_id,
                trace_id=trace_id,
                status=status,
                result_summary=summary,
                latency_ms=latency_ms,
            )
        )
