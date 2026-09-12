import logging
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.factory import AgentFactory
from app.api.agents import router as agents_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.network import router as network_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.repositories.database import Database
from app.repositories.network import NetworkStore
from app.repositories.uow import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)
CallNext = Callable[[Request], Awaitable[Response]]
TRACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)
    database = Database(active_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("application_started")
        yield
        await database.dispose()
        logger.info("application_stopped")

    application = FastAPI(title=active_settings.app_name, version="0.1.0", lifespan=lifespan)
    application.state.settings = active_settings
    application.state.database = database
    application.state.uow_factory = lambda: SqlAlchemyUnitOfWork(database.session_factory)
    application.state.agent_factory = AgentFactory(active_settings)
    application.state.network_store = NetworkStore(database.session_factory)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=bool(active_settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next: CallNext) -> Response:
        supplied_trace_id = request.headers.get("X-Request-ID")
        if supplied_trace_id is not None and TRACE_ID_PATTERN.fullmatch(supplied_trace_id) is None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "invalid_trace_id",
                        "message": "X-Request-ID has an invalid format.",
                    },
                    "trace_id": None,
                },
            )
        trace_id = supplied_trace_id or str(uuid4())
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
    application.include_router(events_router)
    application.include_router(agents_router)
    application.include_router(network_router)
    return application


app = create_app()
