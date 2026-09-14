from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.agents.factory import AgentFactory
from app.core.config import Settings
from app.core.errors import AgentInterpretationFailure
from app.domain.enums import ActionType, AssignmentStatus, OperationalExceptionType
from app.domain.network import OperationalException, RouteResult
from app.domain.organizations import Donor, Driver, Recipient
from app.domain.policy import Policy
from app.domain.rescue import Assignment, Donation, FoodItem, Rescue, RescueAllocation
from app.models import Base
from app.repositories.network import CapacityUnavailable, NetworkStore
from app.repositories.uow import SqlAlchemyUnitOfWork
from app.schemas.recovery import RecoveryProposal
from app.services.demo_network import (
    HARBOR_ID,
    MARKET_SQUARE_ID,
    MAYA_ID,
    RIVERSIDE_ID,
    demo_route_provider,
    seed_demo_network,
)
from app.services.driver_matching import DriverMatchingService
from app.services.exception_agent import ExceptionAgentService
from app.services.matching import (
    EligibilityEngine,
    FeasibilityEngine,
    RecipientMatchingService,
    RecipientScorer,
)
from app.services.recovery import ExceptionService
from app.workflows.hero import run_hero_scenario
from app.workflows.rescue import verify_delivery
from tests.fakes import FakeStrandsModel

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


@pytest.fixture
async def network(
    tmp_path: Path,
) -> AsyncIterator[tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine]]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'network.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_demo_network(factory)
    yield NetworkStore(factory), factory, engine
    await engine.dispose()


async def demo_entities(
    store: NetworkStore,
) -> tuple[Donor, Recipient, Recipient, list[Driver]]:
    donor = await store.get_donor(MARKET_SQUARE_ID)
    recipients = {item.id: item for item in await store.list_recipients()}
    assert donor is not None
    return donor, recipients[HARBOR_ID], recipients[RIVERSIDE_ID], await store.list_drivers()


def donation_and_item() -> tuple[Donation, FoodItem]:
    donation = Donation(
        donor_id=MARKET_SQUARE_ID,
        pickup_window_start=NOW,
        pickup_window_end=NOW + timedelta(hours=2),
    )
    item = FoodItem(
        donation_id=donation.id,
        name="prepared meals",
        quantity=Decimal("36"),
        unit="meals",
        handling_category="prepared_meal",
        requires_refrigeration=True,
        dietary_tags=frozenset({"general"}),
    )
    return donation, item


async def test_eligibility_reports_every_deterministic_blocker(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, _, _ = network
    _, harbor, _, _ = await demo_entities(store)
    _, item = donation_and_item()
    incompatible = harbor.model_copy(
        update={
            "active": False,
            "accepted_food_categories": frozenset({"bakery"}),
            "dietary_capabilities": frozenset(),
            "cold_storage_available": False,
            "available_capacity": 2,
            "service_radius_km": 1,
            "availability": harbor.availability.model_copy(
                update={"opens_minute": 60, "closes_minute": 120}
            ),
            "reliability": 0.5,
        }
    )
    result = EligibilityEngine().evaluate(
        item=item,
        quantity=36,
        recipient=incompatible,
        route=RouteResult(
            distance_km=4,
            travel_time_minutes=12,
            source="test",
            calculated_at=NOW,
        ),
        policy=Policy(reference="inactive", name="inactive", active=False),
        current_time=NOW,
    )

    assert not result.eligible
    assert set(result.blocking_reasons) == {
        "recipient_inactive",
        "food_category_not_accepted",
        "insufficient_capacity",
        "cold_storage_unavailable",
        "dietary_capability_missing",
        "outside_service_area",
        "recipient_closed",
        "inactive_policy",
    }
    assert result.warnings == ("low_historical_reliability",)


async def test_static_routes_scores_and_rankings_are_repeatable(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, _, _ = network
    donor, harbor, _, _ = await demo_entities(store)
    donation, item = donation_and_item()
    route = demo_route_provider().calculate(
        MARKET_SQUARE_ID,
        HARBOR_ID,
        donor.location,
        harbor.location,
        NOW,
    )
    score = RecipientScorer().score(harbor, route, 36, 120, True)
    service = RecipientMatchingService(demo_route_provider())
    arguments = {
        "donor_id": MARKET_SQUARE_ID,
        "donor_location": donor.location,
        "donation": donation,
        "items": [item],
        "recipients": await store.list_recipients(),
        "current_time": NOW,
    }
    first = service.match(**arguments)  # type: ignore[arg-type]
    second = service.match(**arguments)  # type: ignore[arg-type]

    assert route.source == "static-demo-route-matrix"
    assert set(score.components) == {
        "distance",
        "urgency",
        "capacity",
        "priority",
        "reliability",
        "fairness",
    }
    assert first == second
    assert first.chosen_allocations[0].recipient_id == HARBOR_ID


async def test_split_plan_preserves_inventory_and_requires_policy(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, _, _ = network
    donor, harbor, riverside, _ = await demo_entities(store)
    donation, item = donation_and_item()
    partials = [
        harbor.model_copy(update={"available_capacity": 20}),
        riverside.model_copy(update={"available_capacity": 16}),
    ]
    matcher = RecipientMatchingService(demo_route_provider())
    common = {
        "donor_id": MARKET_SQUARE_ID,
        "donor_location": donor.location,
        "donation": donation,
        "items": [item],
        "recipients": partials,
        "current_time": NOW,
    }
    without_policy = matcher.match(**common)  # type: ignore[arg-type]
    with_policy = matcher.match(
        **common,  # type: ignore[arg-type]
        policy=Policy(
            reference="split",
            name="split",
            allowed_amber_actions=frozenset({ActionType.SPLIT_RESCUE}),
        ),
    )

    assert without_policy.chosen_allocations == ()
    assert len(with_policy.chosen_allocations) == 2
    assert sum(item.quantity for item in with_policy.chosen_allocations) == 36
    assert {item.recipient_id for item in with_policy.chosen_allocations} == {
        HARBOR_ID,
        RIVERSIDE_ID,
    }


async def test_feasibility_and_driver_matching_enforce_deadlines_capacity_and_cold_chain(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, _, _ = network
    donor, harbor, _, drivers = await demo_entities(store)
    donation, _ = donation_and_item()
    route = demo_route_provider().calculate(
        MARKET_SQUARE_ID,
        HARBOR_ID,
        donor.location,
        harbor.location,
        NOW,
    )
    result = FeasibilityEngine().evaluate(
        donation=donation,
        recipient=harbor,
        current_time=NOW,
        donor_to_recipient=route,
        driver_arrival_minutes=130,
        requires_refrigeration=True,
        refrigerated_vehicle=False,
        quantity=61,
        vehicle_capacity=60,
    )
    plan = DriverMatchingService(demo_route_provider()).match(
        donor=donor,
        recipient=harbor,
        donation=donation,
        drivers=drivers,
        quantity=36,
        requires_refrigeration=True,
        current_time=NOW,
    )

    assert set(result.blocking_reasons) >= {
        "pickup_deadline_missed",
        "refrigerated_vehicle_required",
        "vehicle_capacity_insufficient",
    }
    assert plan.chosen_driver_id == MAYA_ID
    assert any("refrigerated_vehicle_required" in value for value in plan.rejected_reasons.values())


async def test_capacity_assignment_and_outbox_persist_atomically(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, factory, _ = network
    donor, _, _, _ = await demo_entities(store)
    donation, item = donation_and_item()
    await store.create_donation(donation, [item])
    rescue = Rescue(donation_id=donation.id)
    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.rescues.create(rescue, donor_organization_id=donor.organization_id)
        await uow.commit()
    allocation = RescueAllocation(
        rescue_id=rescue.id,
        recipient_id=HARBOR_ID,
        food_item_id=item.id,
        quantity=Decimal("36"),
        unit="meals",
        trace_id="atomic-test",
    )
    persisted = (await store.reserve_allocations([allocation]))[0]
    assignment = await store.create_assignment(
        Assignment(
            rescue_id=rescue.id,
            allocation_id=persisted.id,
            recipient_id=HARBOR_ID,
            driver_id=MAYA_ID,
            trace_id="atomic-test",
        )
    )

    harbor = next(item for item in await store.list_recipients() if item.id == HARBOR_ID)
    assert harbor.available_capacity == 24
    assert assignment.status is AssignmentStatus.RESERVED
    assert {item.message_type for item in await store.list_outbox()} >= {
        "recipient_assigned",
        "driver_assigned",
    }
    with pytest.raises(CapacityUnavailable, match="driver is not available"):
        await store.create_assignment(
            Assignment(
                rescue_id=rescue.id,
                allocation_id=persisted.id,
                recipient_id=HARBOR_ID,
                driver_id=MAYA_ID,
                trace_id="duplicate-driver",
            )
        )
    released = await store.release_capacity(persisted.id)
    harbor = next(item for item in await store.list_recipients() if item.id == HARBOR_ID)
    assert released.status is AssignmentStatus.CANCELLED
    assert harbor.available_capacity == 60


def test_delivery_verification_sums_split_allocations_and_detects_mismatch() -> None:
    food_item_id = uuid4()
    allocations = [
        RescueAllocation(
            rescue_id=uuid4(),
            recipient_id=uuid4(),
            food_item_id=food_item_id,
            quantity=Decimal("20"),
            unit="meals",
        ),
        RescueAllocation(
            rescue_id=uuid4(),
            recipient_id=uuid4(),
            food_item_id=food_item_id,
            quantity=Decimal("16"),
            unit="meals",
        ),
    ]

    assert verify_delivery(allocations, {food_item_id: 36}).matches
    mismatch = verify_delivery(allocations, {food_item_id: 35})
    assert mismatch.differences[str(food_item_id)] == -1


async def test_exception_agent_accepts_only_deterministic_options() -> None:
    exception = OperationalException(
        rescue_id=uuid4(),
        exception_type=OperationalExceptionType.RECIPIENT_DECLINED,
        context={},
        trace_id="exception-agent-test",
    )
    options = ExceptionService.options(exception)
    settings = Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:")
    accepted = ExceptionAgentService(
        AgentFactory(
            settings,
            model=FakeStrandsModel(
                [
                    RecoveryProposal(
                        strategy=options[0].strategy,
                        reason="Use the next deterministic candidate.",
                    )
                ]
            ),
        )
    )
    proposal = await accepted.choose(exception, options, trace_id=exception.trace_id)
    assert proposal.strategy == options[0].strategy

    bypass = ExceptionAgentService(
        AgentFactory(
            settings,
            model=FakeStrandsModel(
                [
                    {
                        "strategy": "replace_driver",
                        "reason": "Attempt an option that was not offered.",
                    }
                ]
            ),
        )
    )
    with pytest.raises(AgentInterpretationFailure):
        await bypass.choose(exception, options, trace_id=exception.trace_id)


async def test_hero_scenario_uses_real_services_and_completes(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    store, factory, _ = network
    summary = await run_hero_scenario(store, lambda: SqlAlchemyUnitOfWork(factory))

    assert summary.final_rescue_status == "completed"
    assert summary.delivery_verified
    assert summary.trace_ids == ["hero-market-square-001"]
    assert summary.recipient_changes == [f"{HARBOR_ID}->{RIVERSIDE_ID}"]
    assert summary.driver_changes == [f"{MAYA_ID}->{UUID('30000000-0000-4000-8000-000000000003')}"]
    assert summary.exceptions == [
        "recipient_storage_loss:recovered",
        "driver_cancelled:recovered",
        "missing_required_information:recovered",
    ]
    assert any(value.endswith(":resolved") for value in summary.human_decisions)
    assert "substitute_recipient" in summary.autonomous_actions
    assert "search_replacement_driver" in summary.autonomous_actions


async def test_hero_scenario_reruns_on_a_persistent_network(
    network: tuple[NetworkStore, async_sessionmaker[AsyncSession], AsyncEngine],
) -> None:
    """Public demos run the scenario repeatedly against one database; the seed must restore
    the synthetic network's operational baseline while keeping earlier rescues intact."""
    store, factory, _ = network
    first = await run_hero_scenario(store, lambda: SqlAlchemyUnitOfWork(factory))
    await seed_demo_network(factory)
    recipients = {item.id: item for item in await store.list_recipients()}
    assert recipients[HARBOR_ID].cold_storage_available
    assert recipients[HARBOR_ID].available_capacity == recipients[HARBOR_ID].total_capacity
    assert all(driver.available for driver in await store.list_drivers())

    second = await run_hero_scenario(store, lambda: SqlAlchemyUnitOfWork(factory))

    assert second.rescue_id != first.rescue_id
    assert second.final_rescue_status == "completed"
    assert second.delivery_verified
    assert second.recipient_changes == first.recipient_changes
    assert second.driver_changes == first.driver_changes
    assert await store.list_allocations(first.rescue_id)
