from typing import Literal
from uuid import UUID

from pydantic import Field

from app.core.errors import RescueNotFound
from app.domain.audit import AgentAction, ToolExecution
from app.domain.base import DomainModel
from app.domain.enums import ActionAuthority, ActionType
from app.domain.policy import DeterministicPolicyEvaluator, Policy, PolicyEvaluator
from app.repositories.interfaces import UnitOfWork
from app.services.event_processing import UnitOfWorkFactory
from app.tools.contracts import AuthorizedTool, ToolResult


class ProposedAction(DomainModel):
    rescue_id: UUID
    action: ActionType
    agent_name: str = Field(min_length=1, max_length=100)
    input_summary: str = Field(min_length=1, max_length=2000)
    trace_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class ActionExecutionResult(DomainModel):
    action_id: UUID
    tool_execution_id: UUID | None = None
    authority: ActionAuthority
    permitted: bool
    executed: bool
    requires_human: bool
    succeeded: bool
    status: Literal["executed", "denied", "escalated", "failed"]
    policy_reference: str | None = None
    reason: str = Field(min_length=1, max_length=1000)
    result_summary: str | None = Field(default=None, max_length=2000)
    trace_id: str


class AuthorizedActionService:
    """The only application boundary through which future agents may invoke tools."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        evaluator: PolicyEvaluator | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._evaluator = evaluator or DeterministicPolicyEvaluator()

    async def execute(
        self,
        proposal: ProposedAction,
        tool: AuthorizedTool,
        *,
        policy: Policy | None = None,
    ) -> ActionExecutionResult:
        decision = self._evaluator.evaluate(proposal.action, policy)
        if not decision.permitted:
            return await self._record_denial(proposal, decision.authority, decision.reason, policy)

        try:
            async with self._uow_factory() as uow:
                await self._require_rescue(uow, proposal.rescue_id)
                tool_result = await tool.execute(uow=uow)
                action = self._action(
                    proposal,
                    authority=decision.authority,
                    policy_reference=decision.policy_reference,
                    permitted=True,
                    decision_reason=decision.reason,
                    succeeded=True,
                    result_summary=tool_result.summary,
                )
                execution = self._execution(proposal, tool, tool_result, action)
                await uow.agent_actions.append(action)
                await uow.tool_executions.append(execution)
                await uow.commit()
        except Exception as exc:
            return await self._record_failure(
                proposal,
                tool,
                authority=decision.authority,
                policy_reference=decision.policy_reference,
                decision_reason=decision.reason,
                error_type=type(exc).__name__,
            )

        return ActionExecutionResult(
            action_id=action.id,
            tool_execution_id=execution.id,
            authority=decision.authority,
            permitted=True,
            executed=True,
            requires_human=False,
            succeeded=True,
            status="executed",
            policy_reference=decision.policy_reference,
            reason=decision.reason,
            result_summary=tool_result.summary,
            trace_id=proposal.trace_id,
        )

    async def _record_denial(
        self,
        proposal: ProposedAction,
        authority: ActionAuthority,
        reason: str,
        policy: Policy | None,
    ) -> ActionExecutionResult:
        policy_reference = policy.reference if policy is not None else None
        action = self._action(
            proposal,
            authority=authority,
            policy_reference=policy_reference,
            permitted=False,
            decision_reason=reason,
            succeeded=False,
            result_summary="Action was not executed.",
            error_metadata={"code": "human_decision_required"},
        )
        async with self._uow_factory() as uow:
            await self._require_rescue(uow, proposal.rescue_id)
            await uow.agent_actions.append(action)
            await uow.commit()
        requires_human = authority in {ActionAuthority.AMBER, ActionAuthority.RED}
        return ActionExecutionResult(
            action_id=action.id,
            authority=authority,
            permitted=False,
            executed=False,
            requires_human=requires_human,
            succeeded=False,
            status="escalated" if authority is ActionAuthority.RED else "denied",
            policy_reference=policy_reference,
            reason=reason,
            result_summary=action.result_summary,
            trace_id=proposal.trace_id,
        )

    async def _record_failure(
        self,
        proposal: ProposedAction,
        tool: AuthorizedTool,
        *,
        authority: ActionAuthority,
        policy_reference: str | None,
        decision_reason: str,
        error_type: str,
    ) -> ActionExecutionResult:
        error_metadata = {"code": "tool_execution_failed", "error_type": error_type}
        result = ToolResult(summary="Tool execution failed; transaction was rolled back.")
        action = self._action(
            proposal,
            authority=authority,
            policy_reference=policy_reference,
            permitted=True,
            decision_reason=decision_reason,
            succeeded=False,
            result_summary=result.summary,
            error_metadata=error_metadata,
        )
        execution = self._execution(
            proposal,
            tool,
            result,
            action,
            succeeded=False,
            error_metadata=error_metadata,
        )
        async with self._uow_factory() as uow:
            await self._require_rescue(uow, proposal.rescue_id)
            await uow.agent_actions.append(action)
            await uow.tool_executions.append(execution)
            await uow.commit()
        return ActionExecutionResult(
            action_id=action.id,
            tool_execution_id=execution.id,
            authority=authority,
            permitted=True,
            executed=True,
            requires_human=False,
            succeeded=False,
            status="failed",
            policy_reference=policy_reference,
            reason=decision_reason,
            result_summary=result.summary,
            trace_id=proposal.trace_id,
        )

    @staticmethod
    async def _require_rescue(uow: UnitOfWork, rescue_id: UUID) -> None:
        if await uow.rescues.get(rescue_id) is None:
            raise RescueNotFound()

    @staticmethod
    def _action(
        proposal: ProposedAction,
        *,
        authority: ActionAuthority,
        policy_reference: str | None,
        permitted: bool,
        decision_reason: str,
        succeeded: bool,
        result_summary: str,
        error_metadata: dict[str, str] | None = None,
    ) -> AgentAction:
        return AgentAction(
            rescue_id=proposal.rescue_id,
            agent_name=proposal.agent_name,
            action_name=proposal.action.value,
            input_summary=proposal.input_summary,
            result_summary=result_summary,
            authority=authority,
            policy_reference=policy_reference,
            trace_id=proposal.trace_id,
            permitted=permitted,
            decision_reason=decision_reason,
            succeeded=succeeded,
            error_metadata=error_metadata,
        )

    @staticmethod
    def _execution(
        proposal: ProposedAction,
        tool: AuthorizedTool,
        result: ToolResult,
        action: AgentAction,
        *,
        succeeded: bool = True,
        error_metadata: dict[str, str] | None = None,
    ) -> ToolExecution:
        return ToolExecution(
            rescue_id=proposal.rescue_id,
            agent_action_id=action.id,
            agent_name=proposal.agent_name,
            tool_name=tool.name,
            input_summary=proposal.input_summary,
            result_summary=result.summary,
            authority=action.authority,
            policy_reference=action.policy_reference,
            trace_id=proposal.trace_id,
            succeeded=succeeded,
            error_metadata=error_metadata,
        )
