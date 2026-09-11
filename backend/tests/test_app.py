import httpx

from app.core.config import Settings
from app.main import create_app


def test_application_boots() -> None:
    application = create_app()
    assert application.title == "Relay"


async def test_health_endpoint(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


async def test_ready_endpoint_is_structured_for_dependency_checks(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/ready", headers={"X-Request-ID": "test-trace"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-trace"
    assert response.json() == {
        "status": "ready",
        "checks": {"database": {"status": "ok"}},
    }


async def test_invalid_trace_identifier_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "x" * 101})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_trace_id"


async def test_ready_returns_503_when_database_is_unavailable() -> None:
    class UnavailableDatabase:
        async def is_ready(self) -> bool:
            return False

    application = create_app(
        Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:")
    )
    real_database = application.state.database
    application.state.database = UnavailableDatabase()
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
    await real_database.dispose()

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": {"status": "unavailable"}},
    }
