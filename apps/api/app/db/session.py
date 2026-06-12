"""Async SQLAlchemy engine + session factory + RLS-context dependency.

Connections are never used directly; all DB work runs inside an
:class:`AsyncSession` opened by :func:`get_session`. The session is bound to a
**non-superuser** Postgres role that cannot bypass RLS. Per request, we run::

    SET LOCAL app.current_user_id = '<uuid>'
    SET LOCAL app.current_clinic_id = '<uuid>'

so the RLS policies see the right principal.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def reset_engine() -> None:
    """Used by tests to ensure a clean engine when DATABASE_URL changes."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Open a session that auto-commits on success and rolls back on error."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_rls_context(
    session: AsyncSession,
    *,
    user_id: UUID,
    clinic_id: UUID | None = None,
) -> None:
    """Set the per-transaction session variables RLS policies key off.

    Must be called inside a transaction so that ``SET LOCAL`` takes effect.

    Portability: we deliberately avoid ``auth.uid()`` (Supabase-only). The same
    variables work on plain Postgres, RDS, or any other provider.
    """
    await session.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(user_id)},
    )
    if clinic_id is not None:
        await session.execute(
            text("SELECT set_config('app.current_clinic_id', :cid, true)"),
            {"cid": str(clinic_id)},
        )


async def clear_rls_context(session: AsyncSession) -> None:
    """Reset the session vars to the all-zero UUID (no privileges)."""
    await session.execute(text("RESET app.current_user_id"))
    await session.execute(text("RESET app.current_clinic_id"))


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session with no RLS context yet.

    The auth middleware installs the RLS context before any router code runs.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
