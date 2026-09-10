from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class RelayError(Exception):
    """Base class for expected operational errors."""

    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RelayError)
    async def relay_error_handler(request: Request, exc: RelayError) -> JSONResponse:
        payload: dict[str, Any] = {
            "error": {"code": exc.code, "message": exc.message},
            "trace_id": getattr(request.state, "trace_id", None),
        }
        return JSONResponse(status_code=exc.status_code, content=payload)
