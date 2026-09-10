import httpx

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
        "dependencies": {"database": {"status": "not_checked"}},
    }
