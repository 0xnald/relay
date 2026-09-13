"""Execution boundary: local remains the default; AgentCore is opt-in and transport-backed."""

from typing import Protocol

from app.core.errors import (
    AgentExecutionInvalidResponse,
    AgentExecutionTimeout,
    AgentExecutionUnavailable,
)
from app.schemas.agentcore import AgentCoreIntakeRequest, AgentCoreIntakeResponse


class AgentCoreTransport(Protocol):
    async def invoke(self, request: AgentCoreIntakeRequest) -> dict[str, object]: ...


class AgentCoreProvider:
    def __init__(self, transport: AgentCoreTransport) -> None:
        self._transport = transport

    async def intake(self, request: AgentCoreIntakeRequest) -> AgentCoreIntakeResponse:
        try:
            raw = await self._transport.invoke(request)
        except TimeoutError as exc:
            raise AgentExecutionTimeout() from exc
        except OSError as exc:
            raise AgentExecutionUnavailable() from exc
        try:
            return AgentCoreIntakeResponse.model_validate(raw)
        except Exception as exc:
            raise AgentExecutionInvalidResponse() from exc
