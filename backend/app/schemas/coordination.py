from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from app.domain.enums import ActionType
from app.schemas.intake import IntakeModel
from app.services.action_execution import ActionExecutionResult
from app.services.agent_tools import ClarificationResult


class CoordinationProposalKind(StrEnum):
    ACTION = "action"
    CLARIFICATION = "clarification"
    ESCALATION = "escalation"
    NO_ACTION = "no_action"


class CoordinationProposal(IntakeModel):
    kind: CoordinationProposalKind
    action_type: ActionType | None = None
    operational_reason: str = Field(min_length=1, max_length=1000)
    structured_inputs: dict[str, str] = Field(default_factory=dict)
    clarification_target: str | None = Field(default=None, max_length=100)
    clarification_question: str | None = Field(default=None, max_length=1000)
    communication_draft: str | None = Field(default=None, max_length=1000)
    evidence: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> Self:
        if self.kind in {CoordinationProposalKind.ACTION, CoordinationProposalKind.ESCALATION}:
            if self.action_type is None:
                raise ValueError("action_type is required for action or escalation proposals")
        elif self.action_type is not None:
            raise ValueError("action_type is only valid for action or escalation proposals")
        if self.kind is CoordinationProposalKind.CLARIFICATION and (
            not self.clarification_target or not self.clarification_question
        ):
            raise ValueError("clarification target and question are required")
        return self


class CoordinationAgentResponse(IntakeModel):
    proposal: CoordinationProposal
    action_result: ActionExecutionResult | None = None
    clarification_result: ClarificationResult | None = None
    trace_id: str = Field(min_length=1, max_length=100)
