import re
from typing import Any

from pydantic import ValidationError
from strands.types.exceptions import StructuredOutputException

from app.agents.factory import AgentFactory
from app.core.errors import AgentInterpretationFailure
from app.schemas.intake import (
    DonationIntakeResult,
    IntakeAgentResponse,
    IntakeCompletenessResult,
    IntakeCompletenessStatus,
)

AUTHORITATIVE_SAFETY_PATTERN = re.compile(
    r"\b(food|it|this|chicken|meal|donation)\s+is\s+(safe|unsafe|approved for consumption)\b",
    re.IGNORECASE,
)


class IntakeCompletenessEvaluator:
    """Deterministically decides whether extracted facts permit intake progression."""

    def evaluate(self, intake: DonationIntakeResult) -> IntakeCompletenessResult:
        blocking: list[str] = []
        human_review: list[str] = []
        if not intake.items:
            blocking.append("items")
        if intake.items and any(item.quantity is None for item in intake.items):
            blocking.append("quantity")
        if intake.items and any(item.category is None for item in intake.items):
            blocking.append("food_category")
        if intake.pickup_deadline is None and intake.pickup_deadline_text is None:
            blocking.append("pickup_deadline")
        if intake.pickup_location is None:
            blocking.append("pickup_location")
        if any(
            item.prepared_food
            and item.contains_meat
            and (not item.preparation_time_verified or not item.storage_evidence_verified)
            for item in intake.items
        ):
            blocking.append("prepared_food_handling_evidence")
        if intake.contradictions:
            human_review.append("contradictory_intake_evidence")

        if human_review:
            return IntakeCompletenessResult(
                status=IntakeCompletenessStatus.REQUIRES_HUMAN_REVIEW,
                blocking_fields=sorted(set(blocking)),
                human_review_reasons=human_review,
                operational_reason="Contradictory evidence requires human review.",
            )
        if blocking:
            return IntakeCompletenessResult(
                status=IntakeCompletenessStatus.NEEDS_CLARIFICATION,
                blocking_fields=sorted(set(blocking)),
                operational_reason="Required operational or handling facts are missing.",
            )
        return IntakeCompletenessResult(
            status=IntakeCompletenessStatus.READY,
            operational_reason="Required operational facts are present for deterministic checks.",
        )


class IntakeAgentService:
    def __init__(
        self,
        agent_factory: AgentFactory,
        evaluator: IntakeCompletenessEvaluator | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._evaluator = evaluator or IntakeCompletenessEvaluator()

    async def interpret(
        self,
        source_text: str,
        *,
        trace_id: str,
        organization_context: str | None = None,
        actor_identity: str | None = None,
    ) -> IntakeAgentResponse:
        if not source_text.strip():
            raise AgentInterpretationFailure()
        agent = self._agent_factory.create_intake_agent(DonationIntakeResult)
        prompt = self._prompt(source_text, organization_context)
        try:
            result = await agent.invoke_async(
                prompt,
                invocation_state={
                    "trace_id": trace_id,
                    "organization_context": organization_context,
                    "actor_identity": actor_identity,
                },
                structured_output_model=DonationIntakeResult,
            )
            raw: Any = result.structured_output
            interpretation = DonationIntakeResult.model_validate(raw)
            interpretation = interpretation.model_copy(update={"source_text": source_text})
            self._reject_safety_determination(interpretation)
        except (StructuredOutputException, ValidationError, ValueError, TypeError) as exc:
            raise AgentInterpretationFailure() from exc
        return IntakeAgentResponse(
            interpretation=interpretation,
            completeness=self._evaluator.evaluate(interpretation),
            trace_id=trace_id,
        )

    @staticmethod
    def _prompt(source_text: str, organization_context: str | None) -> str:
        context = organization_context or "No additional organization context supplied."
        return (
            "ORGANIZATION_CONTEXT\n"
            f"{context}\n"
            "END_ORGANIZATION_CONTEXT\n\n"
            "EXTERNAL_DONOR_TEXT\n"
            f"{source_text}\n"
            "END_EXTERNAL_DONOR_TEXT"
        )

    @staticmethod
    def _reject_safety_determination(interpretation: DonationIntakeResult) -> None:
        values = interpretation.model_dump(mode="json", exclude={"source_text"})
        if AUTHORITATIVE_SAFETY_PATTERN.search(str(values)):
            raise ValueError("agent output contained an authoritative food-safety determination")
