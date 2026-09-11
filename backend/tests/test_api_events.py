from pathlib import Path
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.domain.enums import OrganizationType
from app.main import create_app
from app.models import Base
from app.models.foundational import OrganizationRecord


async def test_api_ingests_event_and_returns_rescue_and_history(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}",
    )
    application = create_app(settings)
    database = application.state.database
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    organization_id = uuid4()
    async with database.session_factory.begin() as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                name="API Donor",
                kind=OrganizationType.DONOR.value,
            )
        )

    rescue_id = uuid4()
    donation_id = uuid4()
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        ingest = await client.post(
            "/api/v1/events",
            headers={"Idempotency-Key": "api:donation:1", "X-Request-ID": "trace-api"},
            json={
                "rescue_id": str(rescue_id),
                "event_type": "donation_created",
                "actor": "donor",
                "payload": {
                    "donation_id": str(donation_id),
                    "donor_organization_id": str(organization_id),
                },
            },
        )
        rescue = await client.get(f"/api/v1/rescues/{rescue_id}")
        events = await client.get(f"/api/v1/rescues/{rescue_id}/events")
    await database.dispose()

    assert ingest.status_code == 200
    assert ingest.headers["X-Request-ID"] == "trace-api"
    assert ingest.json()["trace_id"] == "trace-api"
    assert ingest.json()["rescue_status_after"] == "received"
    assert rescue.status_code == 200
    assert rescue.json()["donation_id"] == str(donation_id)
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["idempotency_key"] == "api:donation:1"


async def test_api_maps_idempotency_conflict_to_409(tmp_path: Path) -> None:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'conflict.db'}",
    )
    application = create_app(settings)
    database = application.state.database
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    organization_id = uuid4()
    async with database.session_factory.begin() as session:
        session.add(
            OrganizationRecord(
                id=organization_id,
                name="Conflict Donor",
                kind=OrganizationType.DONOR.value,
            )
        )

    base_body = {
        "rescue_id": str(uuid4()),
        "event_type": "donation_created",
        "actor": "donor",
        "payload": {
            "donation_id": str(uuid4()),
            "donor_organization_id": str(organization_id),
        },
    }
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/events", headers={"Idempotency-Key": "api:conflict:1"}, json=base_body
        )
        conflicting_body = {
            "rescue_id": base_body["rescue_id"],
            "event_type": "donation_created",
            "actor": "donor",
            "payload": {
                "donation_id": str(uuid4()),
                "donor_organization_id": str(organization_id),
            },
        }
        conflict = await client.post(
            "/api/v1/events",
            headers={"Idempotency-Key": "api:conflict:1"},
            json=conflicting_body,
        )
    await database.dispose()

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "duplicate_event_conflict"
