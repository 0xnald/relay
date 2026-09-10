import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)
CallNext = Callable[[Request], Awaitable[Response]]


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("application_started")
        yield
        logger.info("application_stopped")

    application = FastAPI(title=active_settings.app_name, version="0.1.0", lifespan=lifespan)
    application.state.settings = active_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=bool(active_settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next: CallNext) -> Response:
        trace_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.trace_id = trace_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        logger.info(
            "request_completed",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    install_error_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
