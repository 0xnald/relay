from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.enums import (
    AssignmentStatus,
    DecisionRequestStatus,
    DriverStatus,
    OperationalExceptionStatus,
)
from app.domain.network import (
    HumanReviewRequest,
    OperationalException,
    OutboxMessage,
    RecoveryAttemptRecord,
)
from app.domain.organizations import (
    ContactMetadata,
    DailyAvailability,
    Donor,
    Driver,
    GeoPoint,
    Recipient,
)
from app.domain.rescue import Assignment, Donation, FoodItem, RescueAllocation
from app.models.network import (
    AssignmentRecord,
    DecisionRequestRecord,
    DonationRecord,
    DonorRecord,
    DriverRecord,
    FoodItemRecord,
    OperationalExceptionRecord,
    OutboxMessageRecord,
    RecipientRecord,
    RecoveryAttemptRecordModel,
    RescueAllocationRecord,
)


class CapacityUnavailable(ValueError):
    pass


class InventoryUnavailable(ValueError):
    pass


def donor_domain(row: DonorRecord) -> Donor:
    return Donor(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        address=row.address,
        location=GeoPoint(latitude=row.latitude, longitude=row.longitude),
        contact=ContactMetadata.model_validate(row.contact),
        synthetic=row.synthetic,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def recipient_domain(row: RecipientRecord) -> Recipient:
    return Recipient(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        active=row.active,
        address=row.address,
        location=GeoPoint(latitude=row.latitude, longitude=row.longitude),
        service_radius_km=row.service_radius_km,
        accepted_food_categories=frozenset(row.accepted_food_categories),
        dietary_capabilities=frozenset(row.dietary_capabilities),
        cold_storage_available=row.cold_storage_available,
        freezer_available=row.freezer_available,
        total_capacity=float(row.total_capacity),
        available_capacity=float(row.available_capacity),
        availability=DailyAvailability(
            opens_minute=row.opens_minute, closes_minute=row.closes_minute
        ),
        priority=row.priority,
        reliability=row.reliability,
        current_load=float(row.current_load),
        contact=ContactMetadata.model_validate(row.contact),
        synthetic=row.synthetic,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def driver_domain(row: DriverRecord) -> Driver:
    return Driver(
        id=row.id,
        name=row.name,
        active=row.active,
        available=row.available,
        current_location=GeoPoint(latitude=row.latitude, longitude=row.longitude),
        vehicle_type=row.vehicle_type,
        vehicle_capacity=float(row.vehicle_capacity),
        refrigerated_vehicle=row.refrigerated_vehicle,
        availability=DailyAvailability(
            opens_minute=row.opens_minute, closes_minute=row.closes_minute
        ),
        reliability=row.reliability,
        status=DriverStatus(row.status),
        contact=ContactMetadata.model_validate(row.contact),
        synthetic=row.synthetic,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def donation_domain(row: DonationRecord) -> Donation:
    return Donation(
        id=row.id,
        donor_id=row.donor_id,
        external_reference=row.external_reference,
        pickup_window_start=row.pickup_window_start,
        pickup_window_end=row.pickup_window_end,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def food_item_domain(row: FoodItemRecord) -> FoodItem:
    return FoodItem(
        id=row.id,
        donation_id=row.donation_id,
        name=row.name,
        quantity=row.quantity,
        unit=row.unit,
        handling_category=row.handling_category,
        allergen_notes=row.allergen_notes,
        requires_refrigeration=row.requires_refrigeration,
        dietary_tags=frozenset(row.dietary_tags),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def allocation_domain(row: RescueAllocationRecord) -> RescueAllocation:
    return RescueAllocation(
        id=row.id,
        rescue_id=row.rescue_id,
        recipient_id=row.recipient_id,
        food_item_id=row.food_item_id,
        quantity=row.quantity,
        unit=row.unit,
        status=AssignmentStatus(row.status),
        trace_id=row.trace_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def assignment_domain(row: AssignmentRecord) -> Assignment:
    return Assignment(
        id=row.id,
        rescue_id=row.rescue_id,
        allocation_id=row.allocation_id,
        recipient_id=row.recipient_id,
        driver_id=row.driver_id,
        status=AssignmentStatus(row.status),
        accepted_at=row.accepted_at,
        cancelled_at=row.cancelled_at,
        trace_id=row.trace_id,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class NetworkStore:
    """Relational operations for the deterministic rescue engine."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_recipients(self) -> list[Recipient]:
        async with self.session_factory() as session:
            rows = (
                await session.scalars(select(RecipientRecord).order_by(RecipientRecord.name))
            ).all()
        return [recipient_domain(row) for row in rows]

    async def list_drivers(self) -> list[Driver]:
        async with self.session_factory() as session:
            rows = (await session.scalars(select(DriverRecord).order_by(DriverRecord.name))).all()
        return [driver_domain(row) for row in rows]

    async def get_donor(self, donor_id: UUID) -> Donor | None:
        async with self.session_factory() as session:
            row = await session.get(DonorRecord, donor_id)
        return donor_domain(row) if row else None

    async def get_recipient(self, recipient_id: UUID) -> Recipient | None:
        async with self.session_factory() as session:
            row = await session.get(RecipientRecord, recipient_id)
        return recipient_domain(row) if row else None

    async def get_driver(self, driver_id: UUID) -> Driver | None:
        async with self.session_factory() as session:
            row = await session.get(DriverRecord, driver_id)
        return driver_domain(row) if row else None

    async def get_donation(self, donation_id: UUID) -> Donation | None:
        async with self.session_factory() as session:
            row = await session.get(DonationRecord, donation_id)
        return donation_domain(row) if row else None

    async def list_food_items(self, donation_id: UUID) -> list[FoodItem]:
        async with self.session_factory() as session:
            rows = (
                await session.scalars(
                    select(FoodItemRecord)
                    .where(FoodItemRecord.donation_id == donation_id)
                    .order_by(FoodItemRecord.created_at, FoodItemRecord.id)
                )
            ).all()
        return [food_item_domain(row) for row in rows]

    async def create_donation(self, donation: Donation, items: Sequence[FoodItem]) -> Donation:
        async with self.session_factory.begin() as session:
            row = DonationRecord(
                id=donation.id,
                donor_id=donation.donor_id,
                external_reference=donation.external_reference,
                pickup_window_start=donation.pickup_window_start,
                pickup_window_end=donation.pickup_window_end,
                notes=donation.notes,
                created_at=donation.created_at,
                updated_at=donation.updated_at,
            )
            session.add(row)
            session.add_all(
                [
                    FoodItemRecord(
                        id=item.id,
                        donation_id=donation.id,
                        name=item.name,
                        quantity=item.quantity,
                        unit=item.unit,
                        handling_category=item.handling_category,
                        allergen_notes=item.allergen_notes,
                        requires_refrigeration=item.requires_refrigeration,
                        dietary_tags=sorted(item.dietary_tags),
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                    )
                    for item in items
                ]
            )
        return donation

    async def reserve_capacity(
        self,
        allocation: RescueAllocation,
    ) -> RescueAllocation:
        async with self.session_factory.begin() as session:
            recipient = await session.scalar(
                select(RecipientRecord)
                .where(RecipientRecord.id == allocation.recipient_id)
                .with_for_update()
            )
            item = await session.get(FoodItemRecord, allocation.food_item_id)
            if recipient is None or item is None:
                raise CapacityUnavailable("recipient or food item does not exist")
            quantity = Decimal(allocation.quantity)
            if recipient.available_capacity < quantity:
                raise CapacityUnavailable("recipient capacity is insufficient")
            allocated = await session.scalar(
                select(func.coalesce(func.sum(RescueAllocationRecord.quantity), 0)).where(
                    RescueAllocationRecord.food_item_id == allocation.food_item_id,
                    RescueAllocationRecord.status != AssignmentStatus.CANCELLED.value,
                )
            )
            if Decimal(allocated or 0) + quantity > item.quantity:
                raise InventoryUnavailable("allocation would duplicate food inventory")
            recipient.available_capacity -= quantity
            recipient.current_load += quantity
            row = RescueAllocationRecord(
                id=allocation.id,
                rescue_id=allocation.rescue_id,
                recipient_id=allocation.recipient_id,
                food_item_id=allocation.food_item_id,
                quantity=quantity,
                unit=allocation.unit,
                status=AssignmentStatus.RESERVED.value,
                trace_id=allocation.trace_id,
                created_at=allocation.created_at,
                updated_at=allocation.updated_at,
            )
            session.add(row)
            await session.flush()
            result = allocation_domain(row)
        return result

    async def release_capacity(self, allocation_id: UUID) -> RescueAllocation:
        async with self.session_factory.begin() as session:
            allocation = await session.scalar(
                select(RescueAllocationRecord)
                .where(RescueAllocationRecord.id == allocation_id)
                .with_for_update()
            )
            if allocation is None:
                raise CapacityUnavailable("allocation does not exist")
            if allocation.status != AssignmentStatus.CANCELLED.value:
                recipient = await session.scalar(
                    select(RecipientRecord)
                    .where(RecipientRecord.id == allocation.recipient_id)
                    .with_for_update()
                )
                if recipient is None:
                    raise CapacityUnavailable("recipient does not exist")
                recipient.available_capacity += allocation.quantity
                recipient.current_load -= allocation.quantity
                allocation.status = AssignmentStatus.CANCELLED.value
            await session.flush()
            result = allocation_domain(allocation)
        return result

    async def list_allocations(self, rescue_id: UUID) -> list[RescueAllocation]:
        async with self.session_factory() as session:
            rows = (
                await session.scalars(
                    select(RescueAllocationRecord)
                    .where(RescueAllocationRecord.rescue_id == rescue_id)
                    .order_by(RescueAllocationRecord.created_at, RescueAllocationRecord.id)
                )
            ).all()
        return [allocation_domain(row) for row in rows]

    async def create_assignment(self, assignment: Assignment) -> Assignment:
        async with self.session_factory.begin() as session:
            driver = await session.scalar(
                select(DriverRecord)
                .where(DriverRecord.id == assignment.driver_id)
                .with_for_update()
            )
            if driver is None or not driver.active or not driver.available:
                raise CapacityUnavailable("driver is not available")
            driver.available = False
            driver.status = DriverStatus.ASSIGNED.value
            row = AssignmentRecord(
                id=assignment.id,
                rescue_id=assignment.rescue_id,
                allocation_id=assignment.allocation_id,
                recipient_id=assignment.recipient_id,
                driver_id=assignment.driver_id,
                status=AssignmentStatus.RESERVED.value,
                accepted_at=assignment.accepted_at,
                cancelled_at=assignment.cancelled_at,
                trace_id=assignment.trace_id,
                version=assignment.version,
                created_at=assignment.created_at,
                updated_at=assignment.updated_at,
            )
            session.add(row)
            session.add(
                OutboxMessageRecord(
                    aggregate_type="assignment",
                    aggregate_id=assignment.id,
                    message_type="driver_assigned",
                    payload={"driver_id": str(assignment.driver_id)},
                    status="pending",
                    attempt_count=0,
                    available_at=assignment.created_at,
                    trace_id=assignment.trace_id,
                )
            )
            await session.flush()
            result = assignment_domain(row)
        return result

    async def cancel_assignment(self, assignment_id: UUID, cancelled_at: datetime) -> Assignment:
        async with self.session_factory.begin() as session:
            row = await session.scalar(
                select(AssignmentRecord)
                .where(AssignmentRecord.id == assignment_id)
                .with_for_update()
            )
            if row is None:
                raise CapacityUnavailable("assignment does not exist")
            if row.status != AssignmentStatus.CANCELLED.value:
                driver = await session.scalar(
                    select(DriverRecord).where(DriverRecord.id == row.driver_id).with_for_update()
                )
                if driver is not None:
                    driver.available = True
                    driver.status = DriverStatus.AVAILABLE.value
                row.status = AssignmentStatus.CANCELLED.value
                row.cancelled_at = cancelled_at
                session.add(
                    OutboxMessageRecord(
                        aggregate_type="assignment",
                        aggregate_id=row.id,
                        message_type="assignment_changed",
                        payload={"reason": "driver_cancelled"},
                        status="pending",
                        attempt_count=0,
                        available_at=cancelled_at,
                        trace_id=row.trace_id,
                    )
                )
            await session.flush()
            result = assignment_domain(row)
        return result

    async def list_assignments(self, rescue_id: UUID) -> list[Assignment]:
        async with self.session_factory() as session:
            rows = (
                await session.scalars(
                    select(AssignmentRecord)
                    .where(AssignmentRecord.rescue_id == rescue_id)
                    .order_by(AssignmentRecord.created_at, AssignmentRecord.id)
                )
            ).all()
        return [assignment_domain(row) for row in rows]

    async def set_recipient_storage(self, recipient_id: UUID, available: bool) -> None:
        async with self.session_factory.begin() as session:
            row = await session.scalar(
                select(RecipientRecord).where(RecipientRecord.id == recipient_id).with_for_update()
            )
            if row is None:
                raise CapacityUnavailable("recipient does not exist")
            row.cold_storage_available = available

    async def add_exception(self, item: OperationalException) -> OperationalException:
        async with self.session_factory.begin() as session:
            session.add(
                OperationalExceptionRecord(
                    id=item.id,
                    rescue_id=item.rescue_id,
                    exception_type=item.exception_type.value,
                    detected_at=item.detected_at,
                    source_event_id=item.source_event_id,
                    severity=item.severity,
                    status=item.status.value,
                    context=item.context,
                    trace_id=item.trace_id,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )
        return item

    async def update_exception_status(
        self, exception_id: UUID, status: OperationalExceptionStatus
    ) -> None:
        async with self.session_factory.begin() as session:
            row = await session.get(OperationalExceptionRecord, exception_id)
            if row is None:
                raise ValueError("exception does not exist")
            row.status = status.value

    async def list_exceptions(self, rescue_id: UUID) -> list[OperationalException]:
        async with self.session_factory() as session:
            rows = (
                await session.scalars(
                    select(OperationalExceptionRecord)
                    .where(OperationalExceptionRecord.rescue_id == rescue_id)
                    .order_by(OperationalExceptionRecord.detected_at)
                )
            ).all()
        return [
            OperationalException(
                id=row.id,
                rescue_id=row.rescue_id,
                exception_type=row.exception_type,
                detected_at=row.detected_at,
                source_event_id=row.source_event_id,
                severity=row.severity,
                status=row.status,
                context=row.context,
                trace_id=row.trace_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def add_recovery(self, attempt: RecoveryAttemptRecord) -> None:
        async with self.session_factory.begin() as session:
            session.add(
                RecoveryAttemptRecordModel(
                    id=attempt.id,
                    rescue_id=attempt.rescue_id,
                    exception_id=attempt.exception_id,
                    strategy=attempt.strategy.value,
                    succeeded=attempt.succeeded,
                    outcome_summary=attempt.outcome_summary,
                    trace_id=attempt.trace_id,
                    created_at=attempt.created_at,
                    updated_at=attempt.updated_at,
                )
            )

    async def add_decision(self, decision: HumanReviewRequest) -> HumanReviewRequest:
        async with self.session_factory.begin() as session:
            session.add(
                DecisionRequestRecord(
                    id=decision.id,
                    rescue_id=decision.rescue_id,
                    exception_id=decision.exception_id,
                    issue=decision.issue,
                    known_evidence=list(decision.known_evidence),
                    missing_evidence=list(decision.missing_evidence),
                    actions_tried=list(decision.actions_tried),
                    allowed_options=list(decision.allowed_options),
                    status=decision.status.value,
                    requested_at=decision.requested_at,
                    resolved_at=decision.resolved_at,
                    resolution=decision.resolution,
                    trace_id=decision.trace_id,
                    created_at=decision.created_at,
                    updated_at=decision.updated_at,
                )
            )
        return decision

    async def resolve_decision(
        self, decision_id: UUID, resolution: str, resolved_at: datetime
    ) -> HumanReviewRequest:
        async with self.session_factory.begin() as session:
            row = await session.scalar(
                select(DecisionRequestRecord)
                .where(DecisionRequestRecord.id == decision_id)
                .with_for_update()
            )
            if row is None or row.status != DecisionRequestStatus.PENDING.value:
                raise ValueError("decision request is not pending")
            row.status = DecisionRequestStatus.RESOLVED.value
            row.resolution = resolution
            row.resolved_at = resolved_at
            await session.flush()
            result = HumanReviewRequest(
                id=row.id,
                rescue_id=row.rescue_id,
                exception_id=row.exception_id,
                issue=row.issue,
                known_evidence=tuple(row.known_evidence),
                missing_evidence=tuple(row.missing_evidence),
                actions_tried=tuple(row.actions_tried),
                allowed_options=tuple(row.allowed_options),
                status=row.status,
                requested_at=row.requested_at,
                resolved_at=row.resolved_at,
                resolution=row.resolution,
                trace_id=row.trace_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        return result

    async def list_decisions(self, rescue_id: UUID | None = None) -> list[HumanReviewRequest]:
        statement = select(DecisionRequestRecord).order_by(DecisionRequestRecord.requested_at)
        if rescue_id is not None:
            statement = statement.where(DecisionRequestRecord.rescue_id == rescue_id)
        async with self.session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [
            HumanReviewRequest(
                id=row.id,
                rescue_id=row.rescue_id,
                exception_id=row.exception_id,
                issue=row.issue,
                known_evidence=tuple(row.known_evidence),
                missing_evidence=tuple(row.missing_evidence),
                actions_tried=tuple(row.actions_tried),
                allowed_options=tuple(row.allowed_options),
                status=row.status,
                requested_at=row.requested_at,
                resolved_at=row.resolved_at,
                resolution=row.resolution,
                trace_id=row.trace_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def list_outbox(self, aggregate_id: UUID | None = None) -> list[OutboxMessage]:
        statement = select(OutboxMessageRecord).order_by(OutboxMessageRecord.created_at)
        if aggregate_id is not None:
            statement = statement.where(OutboxMessageRecord.aggregate_id == aggregate_id)
        async with self.session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [
            OutboxMessage(
                id=row.id,
                aggregate_type=row.aggregate_type,
                aggregate_id=row.aggregate_id,
                message_type=row.message_type,
                payload=row.payload,
                status=row.status,
                attempt_count=row.attempt_count,
                available_at=row.available_at,
                delivered_at=row.delivered_at,
                last_error=row.last_error,
                trace_id=row.trace_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
