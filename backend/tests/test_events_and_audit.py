from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.audit import AgentAction, ToolExecution
from app.domain.enums import ActionAuthority, ActorRole, EventType
from app.domain.events import Event


def test_typed_event_creation() -> None:
    rescue_id = uuid4()
    event = Event(
        rescue_id=rescue_id,
        actor=ActorRole.DONOR,
        event_type=EventType.DONATION_CREATED,
        payload={"source": "intake"},
        idempotency_key="donation:source-42:created",
        trace_id="trace-42",
    )
    assert event.rescue_id == rescue_id
    assert event.timestamp.tzinfo is not None
    assert event.event_type is EventType.DONATION_CREATED


def test_event_requires_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        Event(
            rescue_id=uuid4(),
            actor=ActorRole.SYSTEM,
            event_type=EventType.MISSING_INFORMATION,
            idempotency_key="",
            trace_id="trace-1",
        )


def test_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        Event(
            rescue_id=uuid4(),
            actor=ActorRole.SYSTEM,
            timestamp=datetime(2026, 9, 10),
            event_type=EventType.EVIDENCE_RECEIVED,
            idempotency_key="evidence:1",
            trace_id="trace-1",
        )


def test_event_rejects_oversized_or_deep_payloads() -> None:
    common = {
        "rescue_id": uuid4(),
        "actor": ActorRole.SYSTEM,
        "event_type": EventType.MISSING_INFORMATION,
        "idempotency_key": "payload:limits",
        "trace_id": "trace-limits",
    }
    with pytest.raises(ValidationError, match="64 KiB"):
        Event.model_validate({**common, "payload": {"content": "x" * 65_536}})

    nested: dict[str, object] = {"value": "leaf"}
    for _ in range(9):
        nested = {"child": nested}
    with pytest.raises(ValidationError, match="8 levels"):
        Event.model_validate({**common, "payload": nested})


def test_agent_action_contains_safe_audit_fields() -> None:
    rescue_id = uuid4()
    action = AgentAction(
        rescue_id=rescue_id,
        agent_name="coordination-agent",
        action_name="search_alternate_recipient",
        input_summary="Recipient declined allocation 1.",
        result_summary="Found two eligible recipients.",
        authority=ActionAuthority.GREEN,
        policy_reference="relay-authority-v1",
        trace_id="trace-2",
        timestamp=datetime.now(UTC),
        permitted=True,
        decision_reason="Routine action is autonomously permitted.",
        succeeded=True,
    )
    execution = ToolExecution(
        rescue_id=rescue_id,
        agent_action_id=action.id,
        agent_name=action.agent_name,
        tool_name="recipient_search",
        input_summary="Eligible recipients near pickup.",
        result_summary="Returned two candidates.",
        authority=action.authority,
        policy_reference=action.policy_reference,
        trace_id=action.trace_id,
        succeeded=True,
    )
    assert execution.agent_action_id == action.id
    assert execution.succeeded


def test_green_audit_records_do_not_require_fake_policy_reference() -> None:
    rescue_id = uuid4()
    action = AgentAction(
        rescue_id=rescue_id,
        agent_name="coordination-agent",
        action_name="search_replacement_driver",
        input_summary="Assigned driver cancelled.",
        authority=ActionAuthority.GREEN,
        trace_id="trace-green",
        permitted=True,
        decision_reason="Routine action is autonomously permitted.",
        succeeded=True,
    )
    execution = ToolExecution(
        rescue_id=rescue_id,
        agent_action_id=action.id,
        agent_name=action.agent_name,
        tool_name="driver_search",
        input_summary="Search eligible replacement drivers.",
        authority=ActionAuthority.GREEN,
        trace_id=action.trace_id,
        succeeded=True,
    )

    assert action.policy_reference is None
    assert execution.policy_reference is None


def test_audit_models_reject_hidden_reasoning_fields() -> None:
    with pytest.raises(ValidationError):
        AgentAction.model_validate(
            {
                "rescue_id": uuid4(),
                "agent_name": "coordination-agent",
                "action_name": "notify",
                "input_summary": "Delivery status changed.",
                "authority": ActionAuthority.GREEN,
                "policy_reference": "relay-authority-v1",
                "trace_id": "trace-3",
                "permitted": True,
                "decision_reason": "Routine action is autonomously permitted.",
                "succeeded": True,
                "chain_of_thought": "must never be stored",
            }
        )
