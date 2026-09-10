"""FastAPI application entry point.

Wires configuration, logging, and API routers. Business logic must never
live here or in the routers themselves -- see app/services for that layer
(PROJECT.md section 46, AGENTS.md rule 231).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.errors import AgentOperatorError
from app.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    logger.info("app.startup", environment=settings.application.environment)
    yield
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.application.name,
        debug=settings.application.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.application.api_prefix)

    @app.exception_handler(AgentOperatorError)
    async def handle_agent_operator_error(
        request: Request, exc: AgentOperatorError
    ) -> JSONResponse:
        logger.warning("request.error", code=exc.code, path=str(request.url.path))
        return JSONResponse(status_code=exc.http_status, content={"error": exc.to_dict()})

    @app.exception_handler(NotImplementedError)
    async def handle_not_implemented(request: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(status_code=501, content={"error": {"code": "not_implemented", "message": str(exc)}})

    return app


app = create_app()
