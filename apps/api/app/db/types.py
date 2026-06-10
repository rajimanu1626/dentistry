"""Reusable SQLAlchemy column types."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


UUIDPk = Annotated[
    UUID,
    mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
]

UUIDColumn = Annotated[UUID, mapped_column(PGUUID(as_uuid=True))]

CreatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        default=_utcnow,
    ),
]

UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        default=_utcnow,
        onupdate=_utcnow,
    ),
]
