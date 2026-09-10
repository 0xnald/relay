from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.enums import ActorRole, EvidenceType
from app.domain.operations import Evidence, HandlingRequirement
from app.services.safety import FoodSafetyGate


def requirement() -> HandlingRequirement:
    return HandlingRequirement(
        code="cold-chain-v1",
        required_evidence_types=frozenset({EvidenceType.TEMPERATURE, EvidenceType.TIMESTAMP}),
        maximum_elapsed_time=timedelta(hours=2),
        required_storage_category="chilled",
    )


def evidence(evidence_type: EvidenceType, *, verified: bool = True) -> Evidence:
    return Evidence(
        rescue_id=uuid4(),
        evidence_type=evidence_type,
        submitted_by=ActorRole.DRIVER,
        captured_at=datetime.now(UTC),
        verified=verified,
    )


def test_deterministic_gate_allows_satisfied_requirements() -> None:
    now = datetime.now(UTC)
    assessment = FoodSafetyGate().assess(
        requirements=(requirement(),),
        evidence=(evidence(EvidenceType.TEMPERATURE), evidence(EvidenceType.TIMESTAMP)),
        window_started_at=now - timedelta(minutes=30),
        assessed_at=now,
        storage_category="chilled",
    )
    assert assessment.continue_allowed
    assert not assessment.requires_human


def test_missing_critical_evidence_fails_closed() -> None:
    now = datetime.now(UTC)
    assessment = FoodSafetyGate().assess(
        requirements=(requirement(),),
        evidence=(evidence(EvidenceType.TIMESTAMP),),
        window_started_at=now - timedelta(minutes=30),
        assessed_at=now,
        storage_category="chilled",
    )
    assert not assessment.continue_allowed
    assert assessment.requires_human
    assert assessment.failed_requirements == ("cold-chain-v1",)


def test_unverified_evidence_does_not_satisfy_requirement() -> None:
    now = datetime.now(UTC)
    assessment = FoodSafetyGate().assess(
        requirements=(requirement(),),
        evidence=(
            evidence(EvidenceType.TEMPERATURE, verified=False),
            evidence(EvidenceType.TIMESTAMP),
        ),
        window_started_at=now,
        assessed_at=now,
        storage_category="chilled",
    )
    assert not assessment.continue_allowed


def test_policy_conflict_always_requires_human() -> None:
    now = datetime.now(UTC)
    assessment = FoodSafetyGate().assess(
        requirements=(),
        evidence=(),
        window_started_at=now,
        assessed_at=now,
        storage_category=None,
        policy_conflict=True,
    )
    assert not assessment.continue_allowed
    assert assessment.requires_human
    assert assessment.failed_requirements == ("policy_conflict",)
