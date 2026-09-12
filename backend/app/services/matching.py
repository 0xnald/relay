import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import Field

from app.domain.base import DomainModel
from app.domain.enums import ActionType
from app.domain.network import FeasibilityResult, RouteResult
from app.domain.organizations import GeoPoint, Recipient
from app.domain.policy import Policy
from app.domain.rescue import Donation, FoodItem


class RouteProvider(Protocol):
    def calculate(
        self,
        source_id: UUID,
        destination_id: UUID,
        source: GeoPoint,
        destination: GeoPoint,
        calculated_at: datetime,
    ) -> RouteResult: ...


class StaticRouteProvider:
    """Deterministic route matrix with a haversine fallback; it never claims live traffic."""

    def __init__(self, matrix: Mapping[tuple[UUID, UUID], tuple[float, int]] | None = None) -> None:
        self._matrix = dict(matrix or {})

    def calculate(
        self,
        source_id: UUID,
        destination_id: UUID,
        source: GeoPoint,
        destination: GeoPoint,
        calculated_at: datetime,
    ) -> RouteResult:
        known = self._matrix.get((source_id, destination_id))
        if known is not None:
            return RouteResult(
                distance_km=known[0],
                travel_time_minutes=known[1],
                source="static-demo-route-matrix",
                calculated_at=calculated_at,
            )
        distance = self._haversine(source, destination)
        return RouteResult(
            distance_km=round(distance, 2),
            travel_time_minutes=math.ceil(distance / 25 * 60),
            source="deterministic-haversine-25kmh",
            calculated_at=calculated_at,
        )

    @staticmethod
    def _haversine(source: GeoPoint, destination: GeoPoint) -> float:
        radius = 6371.0
        lat1, lat2 = math.radians(source.latitude), math.radians(destination.latitude)
        delta_lat = math.radians(destination.latitude - source.latitude)
        delta_lon = math.radians(destination.longitude - source.longitude)
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


class EligibilityResult(DomainModel):
    recipient_id: UUID
    eligible: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    matched_categories: tuple[str, ...] = ()
    capacity_available: float
    storage_compatible: bool
    schedule_compatible: bool
    policy_reference: str | None = None


class EligibilityEngine:
    def evaluate(
        self,
        *,
        item: FoodItem,
        quantity: float,
        recipient: Recipient,
        route: RouteResult,
        policy: Policy | None,
        current_time: datetime,
    ) -> EligibilityResult:
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("eligibility time must be timezone-aware")
        blockers: list[str] = []
        warnings: list[str] = []
        if not recipient.active:
            blockers.append("recipient_inactive")
        category_match = item.handling_category in recipient.accepted_food_categories
        if not category_match:
            blockers.append("food_category_not_accepted")
        if recipient.available_capacity < quantity:
            blockers.append("insufficient_capacity")
        storage_compatible = not item.requires_refrigeration or recipient.cold_storage_available
        if not storage_compatible:
            blockers.append("cold_storage_unavailable")
        missing_dietary = item.dietary_tags - recipient.dietary_capabilities
        if missing_dietary:
            blockers.append("dietary_capability_missing")
        if route.distance_km > recipient.service_radius_km:
            blockers.append("outside_service_area")
        minute = current_time.hour * 60 + current_time.minute
        schedule_compatible = (
            recipient.availability.opens_minute <= minute < recipient.availability.closes_minute
        )
        if not schedule_compatible:
            blockers.append("recipient_closed")
        if policy is not None and not policy.active:
            blockers.append("inactive_policy")
        if recipient.reliability < 0.75:
            warnings.append("low_historical_reliability")
        return EligibilityResult(
            recipient_id=recipient.id,
            eligible=not blockers,
            blocking_reasons=tuple(blockers),
            warnings=tuple(warnings),
            matched_categories=(item.handling_category,) if category_match else (),
            capacity_available=recipient.available_capacity,
            storage_compatible=storage_compatible,
            schedule_compatible=schedule_compatible,
            policy_reference=policy.reference if policy else None,
        )


class FeasibilityEngine:
    def evaluate(
        self,
        *,
        donation: Donation,
        recipient: Recipient,
        current_time: datetime,
        donor_to_recipient: RouteResult,
        driver_arrival_minutes: int,
        requires_refrigeration: bool,
        refrigerated_vehicle: bool,
        quantity: float,
        vehicle_capacity: float,
    ) -> FeasibilityResult:
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("feasibility time must be timezone-aware")
        estimated_pickup = current_time + timedelta(minutes=driver_arrival_minutes)
        estimated_delivery = estimated_pickup + timedelta(
            minutes=donor_to_recipient.travel_time_minutes
        )
        closing = current_time.replace(
            hour=recipient.availability.closes_minute // 60 % 24,
            minute=recipient.availability.closes_minute % 60,
            second=0,
            microsecond=0,
        )
        if recipient.availability.closes_minute == 1440:
            closing = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
                days=1
            )
        blockers: list[str] = []
        warnings: list[str] = []
        if estimated_pickup > donation.pickup_window_end:
            blockers.append("pickup_deadline_missed")
        if estimated_delivery > closing:
            blockers.append("recipient_closes_before_delivery")
        if requires_refrigeration and not refrigerated_vehicle:
            blockers.append("refrigerated_vehicle_required")
        if quantity > vehicle_capacity:
            blockers.append("vehicle_capacity_insufficient")
        remaining = math.floor((donation.pickup_window_end - current_time).total_seconds() / 60)
        if 0 <= remaining < 30:
            warnings.append("pickup_window_urgent")
        return FeasibilityResult(
            feasible=not blockers,
            remaining_pickup_minutes=remaining,
            estimated_pickup_at=estimated_pickup,
            estimated_delivery_at=estimated_delivery,
            blocking_reasons=tuple(blockers),
            warnings=tuple(warnings),
        )


class ScoreWeights(DomainModel):
    distance: float = Field(default=0.25, ge=0)
    urgency: float = Field(default=0.15, ge=0)
    capacity: float = Field(default=0.2, ge=0)
    priority: float = Field(default=0.15, ge=0)
    reliability: float = Field(default=0.15, ge=0)
    fairness: float = Field(default=0.1, ge=0)


class RecipientScore(DomainModel):
    recipient_id: UUID
    total_score: float
    components: dict[str, float]
    eligible: bool
    explanation: str


class RecipientScorer:
    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = weights or ScoreWeights()

    def score(
        self,
        recipient: Recipient,
        route: RouteResult,
        quantity: float,
        remaining_pickup_minutes: int,
        eligible: bool,
    ) -> RecipientScore:
        components = {
            "distance": max(0.0, 1 - route.distance_km / max(recipient.service_radius_km, 1)),
            "urgency": max(0.0, 1 - max(remaining_pickup_minutes, 0) / 240),
            "capacity": min(1.0, quantity / max(recipient.available_capacity, 1)),
            "priority": recipient.priority,
            "reliability": recipient.reliability,
            "fairness": max(0.0, 1 - recipient.current_load / max(recipient.total_capacity, 1)),
        }
        total = sum(components[name] * getattr(self.weights, name) for name in components)
        total = round(total if eligible else 0.0, 4)
        explanation = ", ".join(f"{name}={value:.3f}" for name, value in components.items())
        return RecipientScore(
            recipient_id=recipient.id,
            total_score=total,
            components={name: round(value, 4) for name, value in components.items()},
            eligible=eligible,
            explanation=f"Deterministic weighted components: {explanation}.",
        )


class MatchCandidate(DomainModel):
    recipient: Recipient
    eligibility: EligibilityResult
    route: RouteResult
    score: RecipientScore


class PlannedAllocation(DomainModel):
    food_item_id: UUID
    recipient_id: UUID
    quantity: float = Field(gt=0)
    unit: str


class MatchPlan(DomainModel):
    ranked_candidates: tuple[MatchCandidate, ...]
    chosen_allocations: tuple[PlannedAllocation, ...]
    rejected_candidate_reasons: dict[str, tuple[str, ...]]
    policy_reference: str | None


class RecipientMatchingService:
    def __init__(
        self,
        route_provider: RouteProvider,
        eligibility: EligibilityEngine | None = None,
        scorer: RecipientScorer | None = None,
    ) -> None:
        self.routes = route_provider
        self.eligibility = eligibility or EligibilityEngine()
        self.scorer = scorer or RecipientScorer()

    def match(
        self,
        *,
        donor_id: UUID,
        donor_location: GeoPoint,
        donation: Donation,
        items: Sequence[FoodItem],
        recipients: Sequence[Recipient],
        current_time: datetime,
        policy: Policy | None = None,
    ) -> MatchPlan:
        ranked: list[MatchCandidate] = []
        chosen: list[PlannedAllocation] = []
        rejected: dict[str, tuple[str, ...]] = {}
        split_allowed = (
            policy is not None and ActionType.SPLIT_RESCUE in policy.allowed_amber_actions
        )
        for item in items:
            candidates: list[MatchCandidate] = []
            for recipient in recipients:
                route = self.routes.calculate(
                    donor_id, recipient.id, donor_location, recipient.location, current_time
                )
                result = self.eligibility.evaluate(
                    item=item,
                    quantity=float(item.quantity),
                    recipient=recipient,
                    route=route,
                    policy=policy,
                    current_time=current_time,
                )
                score = self.scorer.score(
                    recipient,
                    route,
                    float(item.quantity),
                    math.floor((donation.pickup_window_end - current_time).total_seconds() / 60),
                    result.eligible,
                )
                candidate = MatchCandidate(
                    recipient=recipient, eligibility=result, route=route, score=score
                )
                candidates.append(candidate)
                if not result.eligible:
                    rejected[f"{item.id}:{recipient.id}"] = result.blocking_reasons
            candidates.sort(key=lambda value: (-value.score.total_score, str(value.recipient.id)))
            ranked.extend(candidates)
            eligible = [candidate for candidate in candidates if candidate.eligibility.eligible]
            if eligible:
                chosen.append(
                    PlannedAllocation(
                        food_item_id=item.id,
                        recipient_id=eligible[0].recipient.id,
                        quantity=float(item.quantity),
                        unit=item.unit,
                    )
                )
                continue
            if split_allowed:
                remaining = float(item.quantity)
                partial = [
                    candidate
                    for candidate in candidates
                    if set(candidate.eligibility.blocking_reasons) <= {"insufficient_capacity"}
                    and candidate.recipient.available_capacity > 0
                ]
                for candidate in partial:
                    amount = min(remaining, candidate.recipient.available_capacity)
                    chosen.append(
                        PlannedAllocation(
                            food_item_id=item.id,
                            recipient_id=candidate.recipient.id,
                            quantity=amount,
                            unit=item.unit,
                        )
                    )
                    remaining -= amount
                    if remaining <= 0:
                        break
                if remaining > 0:
                    chosen = [value for value in chosen if value.food_item_id != item.id]
        return MatchPlan(
            ranked_candidates=tuple(ranked),
            chosen_allocations=tuple(chosen),
            rejected_candidate_reasons=rejected,
            policy_reference=policy.reference if policy else None,
        )
