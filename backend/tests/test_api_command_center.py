from pathlib import Path

import httpx

from app.core.config import Settings
from app.main import create_app
from app.models import Base


async def test_demo_hero_populates_dashboard_and_real_rescue_detail(tmp_path: Path) -> None:
    application = create_app(
        Settings(environment="test", database_url=f"sqlite+aiosqlite:///{tmp_path / 'demo.db'}")
    )
    database = application.state.database
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        initial = await client.get("/api/v1/dashboard")
        hero = await client.post("/api/v1/demo/hero")
        dashboard = await client.get("/api/v1/dashboard")
        detail = await client.get(f"/api/v1/rescues/{hero.json()['rescue_id']}/command-center")
    await database.dispose()

    assert initial.status_code == 200
    assert initial.json()["rescues"] == []
    assert hero.status_code == 200
    assert hero.json()["final_rescue_status"] == "completed"
    assert hero.json()["delivery_verified"] is True
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["completed_today"] == 1
    assert detail.status_code == 200
    assert detail.json()["receipt"]["verified"] is True
    assert any(event["kind"] == "driver_cancelled" for event in detail.json()["timeline"])


async def test_demo_mutation_is_unavailable_in_production(tmp_path: Path) -> None:
    application = create_app(
        Settings(
            environment="production", database_url=f"sqlite+aiosqlite:///{tmp_path / 'prod.db'}"
        )
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/demo/hero")
    await application.state.database.dispose()

    assert response.status_code == 404
