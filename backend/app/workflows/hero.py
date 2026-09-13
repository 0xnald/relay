from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.base import DomainModel
from app.domain.enums import (
    ActionType,
    ActorRole,
    EventType,
    OperationalExceptionStatus,
    OperationalExceptionType,
)
from app.domain.policy import Policy
from app.domain.rescue import Donation, FoodItem
from app.repositories.network import NetworkStore
from app.services.action_execution import AuthorizedActionService
from app.services.agent_tools import RelayAgentToolService
from app.services.assignments import AssignmentService
from app.services.demo_network import HARBOR_ID, MARKET_SQUARE_ID, MAYA_ID, demo_route_provider
from app.services.driver_matching import DriverMatchingService
from app.services.event_processing import EventIngestionService, UnitOfWorkFactory
from app.services.human_review import HumanReviewService
from app.services.matching import RecipientMatchingService
from app.services.recovery import ExceptionService, RecoveryStrategyExecutor
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.workflows.rescue import RescueWorkflow, verify_delivery


class HeroScenarioSummary(DomainModel):
    rescue_id: UUID
    donation_id: UUID
    final_rescue_status: str
    allocations: list[dict[str, str]]
    recipient_changes: list[str]
    driver_changes: list[str]
    exceptions: list[str]
    recoveries: list[str]
    human_decisions: list[str]
    autonomous_actions: list[str]
    trace_ids: list[str]
    delivery_verified: bool


async def run_hero_scenario(
    store: NetworkStore, uow_factory: UnitOfWorkFactory
) -> HeroScenarioSummary:
    now = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    trace_id = "hero-market-square-001"
    rescue_id = uuid4()
    donor = await store.get_donor(MARKET_SQUARE_ID)
    if donor is None:
        raise ValueError("demo network must be seeded first")
    donation = Donation(
        donor_id=donor.id,
        external_reference="synthetic-hero-donation",
        pickup_window_start=now,
        pickup_window_end=now + timedelta(hours=3),
        notes="Synthetic hackathon hero scenario.",
    )
    prepared = FoodItem(
        donation_id=donation.id,
        name="prepared chicken meals",
        quantity=Decimal("36"),
        unit="meals",
        handling_category="prepared_meal",
        requires_refrigeration=True,
        dietary_tags=frozenset({"general"}),
    )
    bakery = FoodItem(
        donation_id=donation.id,
        name="bakery items",
        quantity=Decimal("12"),
        unit="items",
        handling_category="bakery",
    )
    policy = Policy(
        reference="relay-demo-policy-v1",
        name="Synthetic demo recovery policy",
        allowed_amber_actions=frozenset(
            {
                ActionType.SPLIT_RESCUE,
                ActionType.SUBSTITUTE_RECIPIENT,
                ActionType.CHANGE_ASSIGNED_DRIVER,
            }
        ),
    )
    events = EventIngestionService(uow_factory)
    matching = RecipientMatchingService(demo_route_provider())
    workflow = RescueWorkflow(store, events, matching)
    _initial_plan, allocations = await workflow.start(
        rescue_id=rescue_id,
        donor=donor,
        donation=donation,
        items=[prepared, bakery],
        current_time=now,
        trace_id=trace_id,
        policy=policy,
    )
    if {item.recipient_id for item in allocations} != {HARBOR_ID}:
        raise AssertionError("hero fixture must initially select Harbor")
    await workflow.emit(
        rescue_id, EventType.RECIPIENT_ACCEPTED, trace_id, actor=ActorRole.RECIPIENT
    )
    await workflow.advance(rescue_id, trace_id, "awaiting-driver")

    driver_matching = DriverMatchingService(demo_route_provider())
    assignment_service = AssignmentService(store)
    assignments = []
    for allocation in allocations:
        recipient = await store.get_recipient(allocation.recipient_id)
        if recipient is None:
            raise AssertionError("selected recipient disappeared")
        item = prepared if allocation.food_item_id == prepared.id else bakery
        driver_plan = driver_matching.match(
            donor=donor,
            recipient=recipient,
            donation=donation,
            drivers=await store.list_drivers(),
            quantity=float(allocation.quantity),
            requires_refrigeration=item.requires_refrigeration,
            current_time=now,
        )
        assignments.append(
            await assignment_service.assign_driver(
                rescue_id=rescue_id,
                allocation=allocation,
                plan=driver_plan,
                trace_id=trace_id,
            )
        )
    maya_assignment = next(item for item in assignments if item.driver_id == MAYA_ID)
    prepared_allocation = next(item for item in allocations if item.food_item_id == prepared.id)
    await workflow.emit(rescue_id, EventType.DRIVER_ACCEPTED, trace_id, actor=ActorRole.DRIVER)
    await workflow.advance(rescue_id, trace_id, "pickup-pending")

    await store.set_recipient_storage(HARBOR_ID, False)
    storage_event = await workflow.emit(
        rescue_id,
        EventType.RECIPIENT_CAPABILITY_LOST,
        trace_id,
        payload={"recipient_id": str(HARBOR_ID), "capability": "cold_storage"},
    )
    exception_service = ExceptionService(store)
    storage_exception = await exception_service.detect(
        rescue_id,
        OperationalExceptionType.RECIPIENT_STORAGE_LOSS,
        context={"allocation_id": str(prepared_allocation.id)},
        source_event_id=storage_event.event_id,
        trace_id=trace_id,
    )
    await workflow.emit(rescue_id, EventType.RECOVERY_STARTED, trace_id)
    replacement_plan = matching.match(
        donor_id=donor.id,
        donor_location=donor.location,
        donation=donation,
        items=[prepared],
        recipients=await store.list_recipients(),
        current_time=now,
        policy=policy,
    )
    actions = RelayAgentToolService(uow_factory, AuthorizedActionService(uow_factory))
    recovery = RecoveryOrchestrator(
        exception_service,
        RecoveryStrategyExecutor(store),
        actions,
    )
    replacement_allocation = await recovery.recover_recipient(
        storage_exception,
        prepared_allocation,
        replacement_plan,
        policy=policy,
        affected_assignment=maya_assignment,
    )
    if replacement_allocation is None:
        raise AssertionError("storage recovery failed")
    maya_assignment = next(
        item for item in await store.list_assignments(rescue_id) if item.id == maya_assignment.id
    )
    await workflow.emit(rescue_id, EventType.RECOVERY_COMPLETED, trace_id)
    await workflow.emit(rescue_id, EventType.RECIPIENT_RECOVERY_RESUMED, trace_id)

    cancellation = await workflow.emit(
        rescue_id, EventType.DRIVER_CANCELLED, trace_id, actor=ActorRole.DRIVER
    )
    driver_exception = await exception_service.detect(
        rescue_id,
        OperationalExceptionType.DRIVER_CANCELLED,
        context={"assignment_id": str(maya_assignment.id)},
        source_event_id=cancellation.event_id,
        trace_id=trace_id,
    )
    await workflow.emit(rescue_id, EventType.RECOVERY_STARTED, trace_id)
    replacement_recipient = await store.get_recipient(replacement_allocation.recipient_id)
    if replacement_recipient is None:
        raise AssertionError("replacement recipient disappeared")
    driver_plan = driver_matching.match(
        donor=donor,
        recipient=replacement_recipient,
        donation=donation,
        drivers=await store.list_drivers(),
        quantity=float(replacement_allocation.quantity),
        requires_refrigeration=True,
        current_time=now,
    )
    replacement_assignment = await recovery.recover_driver(
        driver_exception,
        maya_assignment,
        replacement_allocation,
        driver_plan,
        policy=policy,
    )
    if replacement_assignment is None:
        raise AssertionError("driver recovery failed")
    await workflow.emit(rescue_id, EventType.RECOVERY_COMPLETED, trace_id)
    await workflow.emit(rescue_id, EventType.DRIVER_RECOVERY_RESUMED, trace_id)

    missing_exception = await exception_service.detect(
        rescue_id,
        OperationalExceptionType.MISSING_REQUIRED_INFORMATION,
        context={"missing": "preparation_time_evidence"},
        trace_id=trace_id,
        severity="high",
    )
    await store.update_exception_status(
        missing_exception.id, OperationalExceptionStatus.HUMAN_REVIEW
    )
    reviews = HumanReviewService(store, events)
    decision = await reviews.create(
        missing_exception,
        issue="Prepared-food preparation time evidence is missing.",
        known_evidence=["storage claimed refrigerated"],
        missing_evidence=["verified preparation time"],
        actions_tried=["deterministic evidence check"],
        allowed_options=["approve documented exception", "reject continuation"],
    )
    await reviews.resolve(
        decision.id,
        resolution="approve documented exception",
        actor_id=UUID("40000000-0000-4000-8000-000000000001"),
        trace_id=trace_id,
    )
    await store.update_exception_status(missing_exception.id, OperationalExceptionStatus.RECOVERED)
    await workflow.emit(rescue_id, EventType.WORKFLOW_RESUMED, trace_id)
    await workflow.emit(rescue_id, EventType.PICKUP_CONFIRMED, trace_id, actor=ActorRole.DRIVER)
    await workflow.advance(rescue_id, trace_id, "delivery-pending")
    active_allocations = [
        item for item in await store.list_allocations(rescue_id) if item.status.value != "cancelled"
    ]
    delivered = {item.food_item_id: float(item.quantity) for item in active_allocations}
    verification = verify_delivery(active_allocations, delivered)
    if not verification.matches:
        await workflow.emit(
            rescue_id,
            EventType.DELIVERY_MISMATCH,
            trace_id,
            payload={"differences": str(verification.differences)},
        )
        raise AssertionError("hero delivery did not match allocations")
    await workflow.emit(
        rescue_id, EventType.DELIVERY_CONFIRMED, trace_id, actor=ActorRole.RECIPIENT
    )
    await workflow.advance(rescue_id, trace_id, "completed")

    async with uow_factory() as uow:
        rescue = await uow.rescues.get(rescue_id)
        agent_actions = await uow.agent_actions.list_for_rescue(rescue_id)
        persisted_events = await uow.events.list_for_rescue(rescue_id)
    if rescue is None:
        raise AssertionError("hero rescue disappeared")
    final_allocations = await store.list_allocations(rescue_id)
    exceptions = await store.list_exceptions(rescue_id)
    recoveries = await store.list_recoveries(rescue_id)
    decisions = await store.list_decisions(rescue_id)
    return HeroScenarioSummary(
        rescue_id=rescue.id,
        donation_id=donation.id,
        final_rescue_status=rescue.status.value,
        allocations=[
            {
                "id": str(item.id),
                "recipient_id": str(item.recipient_id),
                "food_item_id": str(item.food_item_id),
                "quantity": str(item.quantity),
                "status": item.status.value,
            }
            for item in final_allocations
        ],
        recipient_changes=[
            f"{prepared_allocation.recipient_id}->{replacement_allocation.recipient_id}"
        ],
        driver_changes=[f"{maya_assignment.driver_id}->{replacement_assignment.driver_id}"],
        exceptions=[f"{item.exception_type.value}:{item.status.value}" for item in exceptions],
        recoveries=[f"{item.strategy.value}:{item.succeeded}" for item in recoveries],
        human_decisions=[f"{item.id}:{item.status.value}" for item in decisions],
        autonomous_actions=[item.action_name for item in agent_actions],
        trace_ids=sorted({item.trace_id for item in persisted_events}),
        delivery_verified=verification.matches,
    )
