from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:")
    application = create_app(settings)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    await application.state.database.dispose()
