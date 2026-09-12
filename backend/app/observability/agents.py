import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from strands.hooks import (
    AfterInvocationEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

logger = logging.getLogger(__name__)


class AgentTelemetry(Protocol):
    def record(self, event: str, attributes: dict[str, str | float | bool]) -> None: ...


class LoggingAgentTelemetry:
    def record(self, event: str, attributes: dict[str, str | float | bool]) -> None:
        logger.info(event, extra=attributes)


@dataclass
class InMemoryAgentTelemetry:
    events: list[tuple[str, dict[str, str | float | bool]]] = field(default_factory=list)

    def record(self, event: str, attributes: dict[str, str | float | bool]) -> None:
        self.events.append((event, attributes))


class SafeAgentHooks(HookProvider):
    """Record lifecycle metadata without prompts, tool inputs, secrets, or model reasoning."""

    def __init__(self, telemetry: AgentTelemetry | None = None) -> None:
        self._telemetry = telemetry or LoggingAgentTelemetry()
        self._started: dict[str, float] = {}

    def register_hooks(self, registry: HookRegistry, **_: Any) -> None:
        registry.add_callback(BeforeInvocationEvent, self.before_invocation)
        registry.add_callback(AfterInvocationEvent, self.after_invocation)
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def before_invocation(self, event: BeforeInvocationEvent) -> None:
        trace_id = str(event.invocation_state.get("trace_id", "unknown"))
        self._started[trace_id] = time.perf_counter()
        self._telemetry.record(
            "agent_started", {"agent_name": event.agent.name, "trace_id": trace_id}
        )

    def after_invocation(self, event: AfterInvocationEvent) -> None:
        trace_id = str(event.invocation_state.get("trace_id", "unknown"))
        started = self._started.pop(trace_id, time.perf_counter())
        self._telemetry.record(
            "agent_completed",
            {
                "agent_name": event.agent.name,
                "trace_id": trace_id,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "succeeded": event.result is not None,
            },
        )

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        self._telemetry.record(
            "agent_tool_invoked",
            {
                "agent_name": event.agent.name,
                "trace_id": str(event.invocation_state.get("trace_id", "unknown")),
                "tool_name": str(event.tool_use["name"]),
            },
        )

    def after_tool(self, event: AfterToolCallEvent) -> None:
        self._telemetry.record(
            "agent_tool_completed" if event.exception is None else "agent_tool_failed",
            {
                "agent_name": event.agent.name,
                "trace_id": str(event.invocation_state.get("trace_id", "unknown")),
                "tool_name": str(event.tool_use["name"]),
                "latency_ms": round((event.duration or 0.0) * 1000, 2),
                "succeeded": event.exception is None,
            },
        )
