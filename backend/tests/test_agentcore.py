
import pytest

from app.core.config import Settings
from app.core.errors import (
    AgentExecutionInvalidResponse,
    AgentExecutionTimeout,
    AgentExecutionUnavailable,
)
from app.main import create_app
from app.schemas.agentcore import AgentCoreIntakeRequest
from app.services.agent_execution import AgentCoreProvider


class Transport:
    def __init__(self, value: object) -> None:
        self.value = value

    async def invoke(self, request: AgentCoreIntakeRequest) -> dict[str, object]:
        if isinstance(self.value, Exception):
            raise self.value
        return self.value  # type: ignore[return-value]


def test_agentcore_request_validates_trace_and_session() -> None:
    request = AgentCoreIntakeRequest(message="Meals", trace_id="relay-1", session_id="session-1")
    assert request.trace_id == "relay-1"
    with pytest.raises(ValueError):
        AgentCoreIntakeRequest(message="")


async def test_agentcore_provider_maps_transport_failures() -> None:
    request = AgentCoreIntakeRequest(message="Meals")
    with pytest.raises(AgentExecutionTimeout):
        await AgentCoreProvider(Transport(TimeoutError())).intake(request)
    with pytest.raises(AgentExecutionUnavailable):
        await AgentCoreProvider(Transport(OSError())).intake(request)
    with pytest.raises(AgentExecutionInvalidResponse):
        await AgentCoreProvider(Transport({"bad": True})).intake(request)


async def test_agent_status_is_safe_and_local_default() -> None:
    app = create_app(Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:"))
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = (await client.get("/api/v1/system/agent-status")).json()
    await app.state.database.dispose()
    assert payload == {
        "execution_mode": "local",
        "provider": "Local Strands",
        "runtime_configured": False,
        "runtime_verified": False,
        "region": "us-east-1",
    }
    assert "secret" not in str(payload).lower()
