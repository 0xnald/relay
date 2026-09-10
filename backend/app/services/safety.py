from datetime import datetime

from app.domain.enums import EvidenceType
from app.domain.operations import Evidence, HandlingRequirement, SafetyAssessment


class FoodSafetyGate:
    """Deterministic food-handling gate; model output is never an input to safety approval."""

    def assess(
        self,
        *,
        requirements: tuple[HandlingRequirement, ...],
        evidence: tuple[Evidence, ...],
        window_started_at: datetime,
        assessed_at: datetime,
        storage_category: str | None,
        policy_conflict: bool = False,
    ) -> SafetyAssessment:
        if policy_conflict:
            return SafetyAssessment(
                continue_allowed=False,
                requires_human=True,
                failed_requirements=("policy_conflict",),
                reason="Conflicting handling policies require human resolution.",
            )

        verified_types = {item.evidence_type for item in evidence if item.verified}
        satisfied: list[str] = []
        failed: list[str] = []
        for requirement in requirements:
            missing = requirement.required_evidence_types - verified_types
            elapsed_invalid = (
                requirement.maximum_elapsed_time is not None
                and assessed_at - window_started_at > requirement.maximum_elapsed_time
            )
            storage_invalid = (
                requirement.required_storage_category is not None
                and storage_category != requirement.required_storage_category
            )
            if missing or elapsed_invalid or storage_invalid:
                failed.append(requirement.code)
            else:
                satisfied.append(requirement.code)

        if failed:
            return SafetyAssessment(
                continue_allowed=False,
                requires_human=True,
                satisfied_requirements=tuple(satisfied),
                failed_requirements=tuple(failed),
                reason="Required handling evidence or constraints were not satisfied.",
            )
        return SafetyAssessment(
            continue_allowed=True,
            requires_human=False,
            satisfied_requirements=tuple(satisfied),
            reason="All configured deterministic handling requirements were satisfied.",
        )


def required_evidence_types(
    requirements: tuple[HandlingRequirement, ...],
) -> frozenset[EvidenceType]:
    return frozenset().union(*(item.required_evidence_types for item in requirements))
