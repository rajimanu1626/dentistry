"""Domain error model + FastAPI exception handlers.

We never leak internal details or PHI in errors. Every error has a stable
``code`` string for the frontend to act on.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base domain error."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "Internal server error."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Resource already exists."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have permission to perform this action."


class ValidationAppError(AppError):
    status_code = 422
    code = "validation_error"
    message = "Request validation failed."


class GoneError(AppError):
    status_code = 410
    code = "gone"
    message = "This resource is no longer available."


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests."


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    logger.warning("app_error", code=exc.code, status=exc.status_code, msg=exc.message)
    return _error_response(exc.status_code, exc.code, exc.message, exc.details or None)


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(exc.status_code, "http_error", str(exc.detail))


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        422,
        "validation_error",
        "Request validation failed.",
        {"errors": exc.errors()},
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return _error_response(500, "internal_error", "An unexpected error occurred.")
