"""Structured logging with PII redaction.

Logs are JSON in production, pretty in development. PHI fields are stripped
before any record is emitted; never log raw patient data.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

_PII_KEYS = {
    "phone",
    "phone_number",
    "address",
    "allergies",
    "medical_history",
    "password",
    "token",
    "authorization",
    "jwt",
    "access_token",
    "refresh_token",
    "dob",
    "date_of_birth",
    "ssn",
    "aadhaar",
    "email",
}


def _redact_pii(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Recursively redact any PII-shaped fields. Defense-in-depth only."""

    def _walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: ("[redacted]" if k.lower() in _PII_KEYS else _walk(v)) for k, v in value.items()
            }
        if isinstance(value, list):
            return [_walk(v) for v in value]
        return value

    return _walk(event_dict)  # type: ignore[return-value]


def configure_logging(*, level: str = "INFO", json_logs: bool = False) -> None:
    """Configure structlog + stdlib logging."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        _redact_pii,
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    log_level = getattr(logging, level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level.upper())

    for noisy in ("uvicorn.access", "watchfiles", "watchfiles.main"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
