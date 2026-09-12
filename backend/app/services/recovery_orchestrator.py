from app.domain.enums import ActionType, OperationalExceptionStatus, RecoveryStrategy
from app.domain.network import OperationalException
from app.domain.policy import Policy
from app.domain.rescue import Assignment, RescueAllocation
from app.schemas.recovery import RecoveryProposal
from app.services.agent_tools import RelayAgentToolService
from app.services.driver_matching import DriverMatchPlan
from app.services.exception_agent import ExceptionAgentService
from app.services.matching import MatchPlan
from app.services.recovery import ExceptionService, RecoveryStrategyExecutor

STRATEGY_ACTIONS = {
    RecoveryStrategy.REMATCH_AFFECTED_ALLOCATION: ActionType.SUBSTITUTE_RECIPIENT,
    RecoveryStrategy.TRY_NEXT_RECIPIENT: ActionType.SEARCH_ALTERNATE_RECIPIENT,
    RecoveryStrategy.REPLACE_DRIVER: ActionType.SEARCH_REPLACEMENT_DRIVER,
    RecoveryStrategy.REQUEST_HUMAN_REVIEW: ActionType.CONTINUE_WITH_MISSING_EVIDENCE,
}


class RecoveryOrchestrator:
    def __init__(
        self,
        exceptions: ExceptionService,
        executor: RecoveryStrategyExecutor,
        actions: RelayAgentToolService,
        exception_agent: ExceptionAgentService | None = None,
    ) -> None:
        self.exceptions = exceptions
        self.executor = executor
        self.actions = actions
        self.exception_agent = exception_agent

    async def select(self, exception: OperationalException, *, trace_id: str) -> RecoveryProposal:
        options = self.exceptions.options(exception)
        if len(options) == 1:
            return RecoveryProposal(strategy=options[0].strategy, reason=options[0].reason)
        if self.exception_agent is None:
            raise ValueError("multiple recovery options require the exception agent")
        return await self.exception_agent.choose(exception, options, trace_id=trace_id)

    async def recover_recipient(
        self,
        exception: OperationalException,
        affected: RescueAllocation,
        plan: MatchPlan,
        *,
        policy: Policy | None,
    ) -> RescueAllocation | None:
        await self.executor.store.update_exception_status(
            exception.id, OperationalExceptionStatus.RECOVERING
        )
        proposal = await self.select(exception, trace_id=exception.trace_id)
        if proposal.strategy is RecoveryStrategy.REQUEST_HUMAN_REVIEW:
            await self.executor.store.update_exception_status(
                exception.id, OperationalExceptionStatus.HUMAN_REVIEW
            )
            return None
        action = await self._authorize(exception, proposal, policy)
        if not action:
            await self.executor.mark_failure(
                exception, proposal.strategy, "Recovery strategy was not authorized."
            )
            return None
        try:
            return await self.executor.rematch_allocation(
                exception=exception, affected=affected, plan=plan
            )
        except Exception as exc:
            await self.executor.mark_failure(
                exception, proposal.strategy, f"Recovery failed: {type(exc).__name__}."
            )
            return None

    async def recover_driver(
        self,
        exception: OperationalException,
        affected: Assignment,
        allocation: RescueAllocation,
        plan: DriverMatchPlan,
        *,
        policy: Policy | None = None,
    ) -> Assignment | None:
        await self.executor.store.update_exception_status(
            exception.id, OperationalExceptionStatus.RECOVERING
        )
        proposal = await self.select(exception, trace_id=exception.trace_id)
        action = await self._authorize(exception, proposal, policy)
        if not action:
            await self.executor.mark_failure(
                exception, proposal.strategy, "Recovery strategy was not authorized."
            )
            return None
        try:
            return await self.executor.replace_driver(
                exception=exception, affected=affected, allocation=allocation, plan=plan
            )
        except Exception as exc:
            await self.executor.mark_failure(
                exception, proposal.strategy, f"Recovery failed: {type(exc).__name__}."
            )
            return None

    async def _authorize(
        self,
        exception: OperationalException,
        proposal: RecoveryProposal,
        policy: Policy | None,
    ) -> bool:
        result = await self.actions.propose_action(
            rescue_id=exception.rescue_id,
            action=STRATEGY_ACTIONS[proposal.strategy],
            operational_reason=proposal.reason,
            structured_inputs={"exception_id": str(exception.id)},
            trace_id=exception.trace_id,
            agent_name="relay-recovery-orchestrator",
            policy=policy,
        )
        return result.permitted and result.succeeded
