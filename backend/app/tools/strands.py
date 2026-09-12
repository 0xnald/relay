from typing import Any, cast

from strands import ToolContext, tool

from app.domain.enums import ActionType
from app.domain.policy import Policy
from app.services.agent_tools import RelayAgentToolService


def _state(tool_context: ToolContext) -> tuple[RelayAgentToolService, dict[str, Any]]:
    state = tool_context.invocation_state
    services = state.get("relay_tool_service")
    if not isinstance(services, RelayAgentToolService):
        raise RuntimeError("Relay tool service is missing from invocation state")
    return services, state


class RelayStrandsTools:
    """The complete bounded tool set registered with Relay's coordination agent."""

    @tool(context=True)
    async def get_rescue(self, tool_context: ToolContext) -> dict[str, Any]:
        """Get the current persisted rescue context for this invocation."""
        services, state = _state(tool_context)
        result = await services.get_rescue(state["rescue_id"])
        return result.model_dump(mode="json")

    @tool(context=True)
    async def get_rescue_events(
        self, limit: int = 20, *, tool_context: ToolContext
    ) -> list[dict[str, Any]]:
        """Get up to 50 recent operational events for this invocation's rescue.

        Args:
            limit: Maximum number of recent events to return.
        """
        services, state = _state(tool_context)
        events = await services.get_rescue_events(state["rescue_id"], limit=limit)
        return [event.model_dump(mode="json") for event in events]

    @tool(context=True)
    def get_policy(self, tool_context: ToolContext) -> dict[str, Any]:
        """Get safe configured policy facts for this rescue invocation."""
        services, state = _state(tool_context)
        return services.get_policy(cast(Policy | None, state.get("policy")))

    @tool(context=True)
    async def evaluate_rescue_constraints(self, tool_context: ToolContext) -> dict[str, Any]:
        """Deterministically evaluate lifecycle and configured policy constraints."""
        services, state = _state(tool_context)
        result = await services.evaluate_constraints(
            state["rescue_id"], cast(Policy | None, state.get("policy"))
        )
        return result.model_dump(mode="json")

    @tool(context=True)
    async def propose_action(
        self,
        action_type: str,
        operational_reason: str,
        structured_inputs: dict[str, str],
        *,
        tool_context: ToolContext,
    ) -> dict[str, Any]:
        """Propose a bounded operational action through Relay authorization.

        Args:
            action_type: A Relay ActionType value.
            operational_reason: Concise operational evidence for the proposal.
            structured_inputs: Small non-secret inputs needed by the action.
        """
        services, state = _state(tool_context)
        action = ActionType(action_type)
        result = await services.propose_action(
            rescue_id=state["rescue_id"],
            action=action,
            operational_reason=operational_reason[:1000],
            structured_inputs=structured_inputs,
            trace_id=state["trace_id"],
            agent_name="relay-coordination",
            policy=cast(Policy | None, state.get("policy")),
        )
        return result.model_dump(mode="json")

    @tool(context=True)
    async def request_information(
        self,
        target: str,
        question: str,
        reason: str,
        *,
        tool_context: ToolContext,
    ) -> dict[str, Any]:
        """Queue an operational clarification request without claiming delivery.

        Args:
            target: Donor, recipient, driver, or coordinator target label.
            question: Concise factual clarification question.
            reason: Operational reason the answer is needed.
        """
        services, state = _state(tool_context)
        result = await services.request_information(
            rescue_id=state["rescue_id"],
            target=target[:100],
            question=question[:1000],
            reason=reason[:1000],
            trace_id=state["trace_id"],
        )
        return result.model_dump(mode="json")

    def registered(self) -> list[object]:
        return [
            self.get_rescue,
            self.get_rescue_events,
            self.get_policy,
            self.evaluate_rescue_constraints,
            self.propose_action,
            self.request_information,
        ]
