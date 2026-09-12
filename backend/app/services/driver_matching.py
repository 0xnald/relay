from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.base import DomainModel
from app.domain.network import FeasibilityResult, RouteResult
from app.domain.organizations import Donor, Driver, Recipient
from app.domain.rescue import Donation
from app.services.matching import FeasibilityEngine, RouteProvider


class DriverCandidate(DomainModel):
    driver: Driver
    route_to_pickup: RouteResult
    feasibility: FeasibilityResult
    score: float = Field(ge=0, le=1)
    explanation: str


class DriverMatchPlan(DomainModel):
    ranked_candidates: tuple[DriverCandidate, ...]
    chosen_driver_id: UUID | None
    rejected_reasons: dict[str, tuple[str, ...]]


class DriverMatchingService:
    def __init__(
        self, route_provider: RouteProvider, feasibility: FeasibilityEngine | None = None
    ) -> None:
        self.routes = route_provider
        self.feasibility = feasibility or FeasibilityEngine()

    def match(
        self,
        *,
        donor: Donor,
        recipient: Recipient,
        donation: Donation,
        drivers: Sequence[Driver],
        quantity: float,
        requires_refrigeration: bool,
        current_time: datetime,
    ) -> DriverMatchPlan:
        candidates: list[DriverCandidate] = []
        rejected: dict[str, tuple[str, ...]] = {}
        delivery_route = self.routes.calculate(
            donor.id, recipient.id, donor.location, recipient.location, current_time
        )
        minute = current_time.hour * 60 + current_time.minute
        for driver in drivers:
            route = self.routes.calculate(
                driver.id, donor.id, driver.current_location, donor.location, current_time
            )
            feasibility = self.feasibility.evaluate(
                donation=donation,
                recipient=recipient,
                current_time=current_time,
                donor_to_recipient=delivery_route,
                driver_arrival_minutes=route.travel_time_minutes,
                requires_refrigeration=requires_refrigeration,
                refrigerated_vehicle=driver.refrigerated_vehicle,
                quantity=quantity,
                vehicle_capacity=driver.vehicle_capacity,
            )
            blockers = list(feasibility.blocking_reasons)
            if not driver.active:
                blockers.append("driver_inactive")
            if not driver.available:
                blockers.append("driver_unavailable")
            if not (driver.availability.opens_minute <= minute < driver.availability.closes_minute):
                blockers.append("driver_outside_availability")
            feasible = not blockers
            if not feasible:
                rejected[str(driver.id)] = tuple(blockers)
                feasibility = feasibility.model_copy(
                    update={"feasible": False, "blocking_reasons": tuple(blockers)}
                )
            distance_component = max(0.0, 1 - route.distance_km / 30)
            score = round(
                (0.55 * distance_component + 0.45 * driver.reliability) if feasible else 0.0,
                4,
            )
            candidates.append(
                DriverCandidate(
                    driver=driver,
                    route_to_pickup=route,
                    feasibility=feasibility,
                    score=score,
                    explanation=(
                        f"Deterministic driver score: distance={distance_component:.3f}, "
                        f"reliability={driver.reliability:.3f}."
                    ),
                )
            )
        candidates.sort(key=lambda value: (-value.score, str(value.driver.id)))
        selected = next(
            (value.driver.id for value in candidates if value.feasibility.feasible), None
        )
        return DriverMatchPlan(
            ranked_candidates=tuple(candidates),
            chosen_driver_id=selected,
            rejected_reasons=rejected,
        )
