"""FastAPI application factory.

This is the only entry point. Tests construct an instance via :func:`create_app`;
the dev server uses ``app = create_app()`` at module load.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.routers import auth, health, media, patients, platform, visits
from app.sharing import router as sharing_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.is_production)
    logger = get_logger(__name__)
    logger.info(
        "api_starting",
        app_env=settings.app_env,
        version=__version__,
        identity_provider=settings.identity_provider,
    )
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="clinic-crm API",
        version=__version__,
        description="Multi-tenant dental clinic CRM.",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(platform.router)
    app.include_router(patients.router)
    app.include_router(visits.visits_router)
    app.include_router(visits.history_router)
    app.include_router(visits.rx_router)
    app.include_router(visits.templates_router)
    app.include_router(media.router)
    app.include_router(sharing_router.internal_router)
    app.include_router(sharing_router.external_admin_router)
    app.include_router(sharing_router.external_public_router)

    # SlowAPI requires the limiter to be attached to the app + an exception handler.
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = sharing_router.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    return app


app = create_app()
