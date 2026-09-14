from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse


class RelayError(Exception):
    """Base class for expected operational errors."""

    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class RescueNotFound(RelayError):
    def __init__(self) -> None:
        super().__init__("rescue_not_found", "The requested rescue was not found.", status_code=404)


class DuplicateEventConflict(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "duplicate_event_conflict",
            "The idempotency key was already used for a different event.",
            status_code=409,
        )


class UnsupportedEvent(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "unsupported_event", "This event type is not supported for processing.", status_code=422
        )


class InvalidEventPayload(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_event_payload",
            "The event payload does not match the required schema.",
            status_code=422,
        )


class EventStateConflict(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "event_state_conflict",
            "The event is not valid for the rescue's current state.",
            status_code=409,
        )


class ConcurrentModification(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "concurrent_modification",
            "The rescue changed during processing; retry with fresh state.",
            status_code=409,
        )


class PolicyDenied(RelayError):
    def __init__(self) -> None:
        super().__init__("policy_denied", "Policy does not authorize this action.", status_code=403)


class HumanDecisionRequired(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "human_decision_required",
            "This action requires an explicit human decision.",
            status_code=409,
        )


class AgentInterpretationFailure(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "agent_interpretation_failure",
            "The agent could not produce a valid structured interpretation.",
            status_code=422,
        )


class AgentExecutionUnavailable(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "agent_execution_unavailable",
            "The configured agent runtime is unavailable.",
            status_code=503,
        )


class AgentExecutionTimeout(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "agent_execution_timeout", "The configured agent runtime timed out.", status_code=504
        )


class AgentExecutionInvalidResponse(RelayError):
    def __init__(self) -> None:
        super().__init__(
            "agent_execution_invalid_response",
            "The agent runtime returned an invalid response.",
            status_code=502,
        )


def install_error_handlers(app: "FastAPI") -> None:
    # Web dependencies are loaded only for FastAPI application setup. The
    # narrow AgentCore intake runtime imports these error types without FastAPI.
    from fastapi.responses import JSONResponse

    @app.exception_handler(RelayError)
    async def relay_error_handler(request: "Request", exc: RelayError) -> "JSONResponse":
        payload: dict[str, Any] = {
            "error": {"code": exc.code, "message": exc.message},
            "trace_id": getattr(request.state, "trace_id", None),
        }
        return JSONResponse(status_code=exc.status_code, content=payload)
