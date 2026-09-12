from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.enums import DriverStatus, OrganizationType
from app.models.foundational import OrganizationRecord
from app.models.network import DonorRecord, DriverRecord, RecipientRecord
from app.services.matching import StaticRouteProvider

MARKET_SQUARE_ID = UUID("10000000-0000-4000-8000-000000000001")
HARBOR_ID = UUID("20000000-0000-4000-8000-000000000001")
RIVERSIDE_ID = UUID("20000000-0000-4000-8000-000000000002")
NORTHSIDE_ID = UUID("20000000-0000-4000-8000-000000000003")
MAYA_ID = UUID("30000000-0000-4000-8000-000000000001")
DANIEL_ID = UUID("30000000-0000-4000-8000-000000000002")
LENA_ID = UUID("30000000-0000-4000-8000-000000000003")


@dataclass(frozen=True, slots=True)
class DemoNetworkIds:
    donor_id: UUID = MARKET_SQUARE_ID
    harbor_id: UUID = HARBOR_ID
    riverside_id: UUID = RIVERSIDE_ID
    northside_id: UUID = NORTHSIDE_ID
    maya_id: UUID = MAYA_ID
    daniel_id: UUID = DANIEL_ID
    lena_id: UUID = LENA_ID


def demo_route_provider() -> StaticRouteProvider:
    return StaticRouteProvider(
        {
            (MARKET_SQUARE_ID, HARBOR_ID): (4.0, 12),
            (MARKET_SQUARE_ID, RIVERSIDE_ID): (8.0, 20),
            (MARKET_SQUARE_ID, NORTHSIDE_ID): (6.0, 18),
            (MAYA_ID, MARKET_SQUARE_ID): (2.0, 7),
            (DANIEL_ID, MARKET_SQUARE_ID): (5.0, 14),
            (LENA_ID, MARKET_SQUARE_ID): (7.0, 18),
        }
    )


async def seed_demo_network(factory: async_sessionmaker[AsyncSession]) -> DemoNetworkIds:
    """Idempotently seed explicitly synthetic actors for demos and tests."""
    async with factory.begin() as session:
        if await session.get(DonorRecord, MARKET_SQUARE_ID) is not None:
            return DemoNetworkIds()
        donor_org = UUID("11000000-0000-4000-8000-000000000001")
        recipient_orgs = [
            UUID("21000000-0000-4000-8000-000000000001"),
            UUID("21000000-0000-4000-8000-000000000002"),
            UUID("21000000-0000-4000-8000-000000000003"),
        ]
        session.add_all(
            [
                OrganizationRecord(
                    id=donor_org, name="Market Square [DEMO]", kind=OrganizationType.DONOR.value
                ),
                *[
                    OrganizationRecord(id=org, name=name, kind=OrganizationType.RECIPIENT.value)
                    for org, name in zip(
                        recipient_orgs,
                        (
                            "Harbor Community Kitchen [DEMO]",
                            "Riverside Shelter [DEMO]",
                            "Northside Food Pantry [DEMO]",
                        ),
                        strict=True,
                    )
                ],
            ]
        )
        session.add(
            DonorRecord(
                id=MARKET_SQUARE_ID,
                organization_id=donor_org,
                name="Market Square",
                address="1 Market Square, Demo City",
                latitude=6.5244,
                longitude=3.3792,
                contact={"name": "Demo donor desk", "email": "market@example.invalid"},
                synthetic=True,
            )
        )
        session.add_all(
            [
                RecipientRecord(
                    id=HARBOR_ID,
                    organization_id=recipient_orgs[0],
                    name="Harbor Community Kitchen",
                    active=True,
                    address="5 Harbor Road, Demo City",
                    latitude=6.53,
                    longitude=3.39,
                    service_radius_km=20,
                    accepted_food_categories=["prepared_meal", "bakery"],
                    dietary_capabilities=["general"],
                    cold_storage_available=True,
                    freezer_available=False,
                    total_capacity=Decimal("60"),
                    available_capacity=Decimal("60"),
                    opens_minute=480,
                    closes_minute=1260,
                    priority=0.9,
                    reliability=0.95,
                    current_load=Decimal("0"),
                    contact={"email": "harbor@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
                RecipientRecord(
                    id=RIVERSIDE_ID,
                    organization_id=recipient_orgs[1],
                    name="Riverside Shelter",
                    active=True,
                    address="18 Riverside Lane, Demo City",
                    latitude=6.55,
                    longitude=3.4,
                    service_radius_km=25,
                    accepted_food_categories=["prepared_meal"],
                    dietary_capabilities=["general", "halal"],
                    cold_storage_available=True,
                    freezer_available=True,
                    total_capacity=Decimal("45"),
                    available_capacity=Decimal("45"),
                    opens_minute=420,
                    closes_minute=1320,
                    priority=0.7,
                    reliability=0.9,
                    current_load=Decimal("0"),
                    contact={"email": "riverside@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
                RecipientRecord(
                    id=NORTHSIDE_ID,
                    organization_id=recipient_orgs[2],
                    name="Northside Food Pantry",
                    active=True,
                    address="40 North Road, Demo City",
                    latitude=6.58,
                    longitude=3.37,
                    service_radius_km=18,
                    accepted_food_categories=["bakery", "produce"],
                    dietary_capabilities=["general"],
                    cold_storage_available=False,
                    freezer_available=False,
                    total_capacity=Decimal("30"),
                    available_capacity=Decimal("30"),
                    opens_minute=540,
                    closes_minute=1140,
                    priority=0.6,
                    reliability=0.84,
                    current_load=Decimal("0"),
                    contact={"email": "northside@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
            ]
        )
        session.add_all(
            [
                DriverRecord(
                    id=MAYA_ID,
                    name="Maya",
                    active=True,
                    available=True,
                    latitude=6.522,
                    longitude=3.377,
                    vehicle_type="refrigerated van",
                    vehicle_capacity=Decimal("60"),
                    refrigerated_vehicle=True,
                    opens_minute=420,
                    closes_minute=1320,
                    reliability=0.97,
                    status=DriverStatus.AVAILABLE.value,
                    contact={"email": "maya@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
                DriverRecord(
                    id=DANIEL_ID,
                    name="Daniel",
                    active=True,
                    available=True,
                    latitude=6.54,
                    longitude=3.38,
                    vehicle_type="van",
                    vehicle_capacity=Decimal("50"),
                    refrigerated_vehicle=False,
                    opens_minute=480,
                    closes_minute=1200,
                    reliability=0.88,
                    status=DriverStatus.AVAILABLE.value,
                    contact={"email": "daniel@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
                DriverRecord(
                    id=LENA_ID,
                    name="Lena",
                    active=True,
                    available=True,
                    latitude=6.56,
                    longitude=3.395,
                    vehicle_type="refrigerated car",
                    vehicle_capacity=Decimal("48"),
                    refrigerated_vehicle=True,
                    opens_minute=360,
                    closes_minute=1380,
                    reliability=0.93,
                    status=DriverStatus.AVAILABLE.value,
                    contact={"email": "lena@example.invalid"},
                    synthetic=True,
                    version=1,
                ),
            ]
        )
    return DemoNetworkIds()
