from collections.abc import Sequence
from uuid import UUID

from pydantic import Field

from app.domain.base import DomainModel
from app.domain.enums import (
    OperationalExceptionStatus,
    OperationalExceptionType,
    RecoveryStrategy,
)
from app.domain.network import OperationalException, RecoveryAttemptRecord
from app.domain.rescue import Assignment, RescueAllocation
from app.repositories.network import NetworkStore
from app.services.driver_matching import DriverMatchPlan
from app.services.matching import MatchPlan


class RecoveryOption(DomainModel):
    strategy: RecoveryStrategy
    authority_action: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)


class ExceptionService:
    def __init__(self, store: NetworkStore) -> None:
        self.store = store

    async def detect(
        self,
        rescue_id: UUID,
        exception_type: OperationalExceptionType,
        *,
        context: dict[str, str],
        trace_id: str,
        source_event_id: UUID | None = None,
        severity: str = "medium",
    ) -> OperationalException:
        item = OperationalException(
            rescue_id=rescue_id,
            exception_type=exception_type,
            source_event_id=source_event_id,
            severity=severity,
            context=context,
            trace_id=trace_id,
        )
        return await self.store.add_exception(item)

    @staticmethod
    def options(item: OperationalException) -> tuple[RecoveryOption, ...]:
        if item.exception_type in {
            OperationalExceptionType.RECIPIENT_STORAGE_LOSS,
            OperationalExceptionType.RECIPIENT_CAPACITY_LOSS,
        }:
            return (
                RecoveryOption(
                    strategy=RecoveryStrategy.REMATCH_AFFECTED_ALLOCATION,
                    authority_action="substitute_recipient",
                    reason="Re-run deterministic matching for only the affected allocation.",
                ),
            )
        if item.exception_type in {
            OperationalExceptionType.RECIPIENT_DECLINED,
            OperationalExceptionType.RECIPIENT_TIMEOUT,
        }:
            return (
                RecoveryOption(
                    strategy=RecoveryStrategy.TRY_NEXT_RECIPIENT,
                    authority_action="search_alternate_recipient",
                    reason="Use the next eligible candidate from deterministic ranking.",
                ),
                RecoveryOption(
                    strategy=RecoveryStrategy.REMATCH_AFFECTED_ALLOCATION,
                    authority_action="substitute_recipient",
                    reason="Recompute candidates if the earlier ranking may be stale.",
                ),
            )
        if item.exception_type in {
            OperationalExceptionType.DRIVER_CANCELLED,
            OperationalExceptionType.DRIVER_DELAYED,
        }:
            return (
                RecoveryOption(
                    strategy=RecoveryStrategy.REPLACE_DRIVER,
                    authority_action="search_replacement_driver",
                    reason="Select the highest-ranked currently feasible replacement driver.",
                ),
            )
        return (
            RecoveryOption(
                strategy=RecoveryStrategy.REQUEST_HUMAN_REVIEW,
                authority_action="continue_with_missing_evidence",
                reason="No safe deterministic recovery can resolve the exception.",
            ),
        )


class RecoveryStrategyExecutor:
    def __init__(self, store: NetworkStore) -> None:
        self.store = store

    async def rematch_allocation(
        self,
        *,
        exception: OperationalException,
        affected: RescueAllocation,
        plan: MatchPlan,
        affected_assignment: Assignment | None = None,
    ) -> RescueAllocation:
        replacements = [
            candidate
            for candidate in plan.chosen_allocations
            if candidate.food_item_id == affected.food_item_id
            and candidate.recipient_id != affected.recipient_id
        ]
        if len(replacements) != 1:
            raise ValueError("recovery requires exactly one feasible replacement allocation")
        replacement = RescueAllocation(
            rescue_id=affected.rescue_id,
            recipient_id=replacements[0].recipient_id,
            food_item_id=affected.food_item_id,
            quantity=replacements[0].quantity,
            unit=affected.unit,
            trace_id=exception.trace_id,
        )
        persisted = await self.store.reassign_allocation(
            affected.id,
            replacement,
            assignment_id=affected_assignment.id if affected_assignment is not None else None,
        )
        await self._record(
            exception,
            RecoveryStrategy.REMATCH_AFFECTED_ALLOCATION,
            True,
            f"Allocation moved to recipient {persisted.recipient_id}.",
        )
        return persisted

    async def replace_driver(
        self,
        *,
        exception: OperationalException,
        affected: Assignment,
        allocation: RescueAllocation,
        plan: DriverMatchPlan,
    ) -> Assignment:
        if plan.chosen_driver_id is None:
            raise ValueError("no feasible replacement driver")
        proposed = Assignment(
            rescue_id=affected.rescue_id,
            allocation_id=allocation.id,
            recipient_id=allocation.recipient_id,
            driver_id=plan.chosen_driver_id,
            trace_id=exception.trace_id,
        )
        replacement = await self.store.replace_assignment(
            affected.id, proposed, exception.detected_at
        )
        await self._record(
            exception,
            RecoveryStrategy.REPLACE_DRIVER,
            True,
            f"Driver changed from {affected.driver_id} to {replacement.driver_id}.",
        )
        return replacement

    async def mark_failure(
        self, exception: OperationalException, strategy: RecoveryStrategy, summary: str
    ) -> None:
        await self._record(exception, strategy, False, summary)
        await self.store.update_exception_status(
            exception.id, OperationalExceptionStatus.HUMAN_REVIEW
        )

    async def _record(
        self,
        exception: OperationalException,
        strategy: RecoveryStrategy,
        succeeded: bool,
        summary: str,
    ) -> None:
        await self.store.add_recovery(
            RecoveryAttemptRecord(
                rescue_id=exception.rescue_id,
                exception_id=exception.id,
                strategy=strategy,
                succeeded=succeeded,
                outcome_summary=summary,
                trace_id=exception.trace_id,
            )
        )
        await self.store.update_exception_status(
            exception.id,
            OperationalExceptionStatus.RECOVERED
            if succeeded
            else OperationalExceptionStatus.HUMAN_REVIEW,
        )


def choose_single_option(options: Sequence[RecoveryOption]) -> RecoveryOption | None:
    return options[0] if len(options) == 1 else None
