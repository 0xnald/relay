from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:")
    transport = httpx.ASGITransport(app=create_app(settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
