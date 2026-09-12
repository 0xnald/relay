from collections.abc import Sequence
from uuid import UUID

from app.domain.enums import AssignmentStatus
from app.domain.rescue import Assignment, RescueAllocation
from app.repositories.network import NetworkStore
from app.services.driver_matching import DriverMatchPlan
from app.services.matching import MatchPlan


class AllocationService:
    def __init__(self, store: NetworkStore) -> None:
        self.store = store

    async def reserve_plan(
        self, rescue_id: UUID, plan: MatchPlan, trace_id: str
    ) -> list[RescueAllocation]:
        allocations = [
            RescueAllocation(
                rescue_id=rescue_id,
                recipient_id=item.recipient_id,
                food_item_id=item.food_item_id,
                quantity=item.quantity,
                unit=item.unit,
                status=AssignmentStatus.PROPOSED,
                trace_id=trace_id,
            )
            for item in plan.chosen_allocations
        ]
        return await self.store.reserve_allocations(allocations)

    async def release(self, allocation_id: UUID) -> RescueAllocation:
        return await self.store.release_capacity(allocation_id)


class AssignmentService:
    def __init__(self, store: NetworkStore) -> None:
        self.store = store

    async def assign_driver(
        self,
        *,
        rescue_id: UUID,
        allocation: RescueAllocation,
        plan: DriverMatchPlan,
        trace_id: str,
    ) -> Assignment:
        if plan.chosen_driver_id is None:
            raise ValueError("no feasible driver")
        assignment = Assignment(
            rescue_id=rescue_id,
            allocation_id=allocation.id,
            recipient_id=allocation.recipient_id,
            driver_id=plan.chosen_driver_id,
            status=AssignmentStatus.PROPOSED,
            trace_id=trace_id,
        )
        return await self.store.create_assignment(assignment)

    async def assign_all(
        self,
        rescue_id: UUID,
        allocations: Sequence[tuple[RescueAllocation, DriverMatchPlan]],
        trace_id: str,
    ) -> list[Assignment]:
        results: list[Assignment] = []
        for allocation, plan in allocations:
            results.append(
                await self.assign_driver(
                    rescue_id=rescue_id,
                    allocation=allocation,
                    plan=plan,
                    trace_id=trace_id,
                )
            )
        return results
