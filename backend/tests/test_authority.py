from app.domain.enums import ActionAuthority, ActionType, OrganizationType
from app.domain.organizations import Organization
from app.domain.policy import DeterministicPolicyEvaluator, Policy


def test_green_action_is_autonomously_permitted() -> None:
    decision = DeterministicPolicyEvaluator().evaluate(ActionType.SEARCH_REPLACEMENT_DRIVER)
    assert decision.authority is ActionAuthority.GREEN
    assert decision.permitted
    assert not decision.requires_human


def test_amber_action_requires_explicit_policy_permission() -> None:
    evaluator = DeterministicPolicyEvaluator()
    denied = evaluator.evaluate(ActionType.SPLIT_RESCUE)
    policy = Policy(
        reference="recipient-policy-v1",
        name="Recipient substitution policy",
        allowed_amber_actions=frozenset({ActionType.SPLIT_RESCUE}),
    )
    allowed = evaluator.evaluate(ActionType.SPLIT_RESCUE, policy)

    assert not denied.permitted
    assert denied.requires_human
    assert allowed.permitted
    assert allowed.policy_reference == "recipient-policy-v1"


def test_inactive_policy_does_not_authorize_amber_action() -> None:
    policy = Policy(
        reference="inactive-policy",
        name="Inactive policy",
        active=False,
        allowed_amber_actions=frozenset({ActionType.CHANGE_ASSIGNED_DRIVER}),
    )
    decision = DeterministicPolicyEvaluator().evaluate(ActionType.CHANGE_ASSIGNED_DRIVER, policy)
    assert not decision.permitted
    assert decision.requires_human


def test_red_action_always_requires_human_even_when_listed_in_policy() -> None:
    policy = Policy(
        reference="unsafe-policy",
        name="Cannot bypass safety boundary",
    )
    decision = DeterministicPolicyEvaluator().evaluate(
        ActionType.CONTINUE_WITH_MISSING_EVIDENCE, policy
    )
    assert decision.authority is ActionAuthority.RED
    assert not decision.permitted
    assert decision.requires_human


def test_organization_model_uses_typed_kind() -> None:
    organization = Organization(
        name="Community Pantry", organization_type=OrganizationType.RECIPIENT
    )
    assert organization.organization_type is OrganizationType.RECIPIENT
