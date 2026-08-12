"""Reuse the testcontainers Postgres fixture from integration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.conftest import (  # noqa: F401 -- re-export fixtures
    apply_migrations,
    database_url,
    database_url_sync,
    db_session,
    postgres_container,
)

RLS_TEST_ROLE = "clinic_rls_test"


@pytest.fixture(scope="session", autouse=True)
def rls_test_role(request: pytest.FixtureRequest) -> None:
    """Create a NOBYPASSRLS role so RLS policies apply during tests."""
    sync_url: str = request.getfixturevalue("database_url_sync")
    request.getfixturevalue("apply_migrations")
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                DO $$ BEGIN
                  CREATE ROLE {RLS_TEST_ROLE} LOGIN NOBYPASSRLS;
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
                """
            )
        )
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {RLS_TEST_ROLE}"))
        conn.execute(
            text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                f"TO {RLS_TEST_ROLE}"
            )
        )
        conn.execute(
            text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RLS_TEST_ROLE}")
        )
    engine.dispose()


async def enter_superuser(session: AsyncSession) -> None:
    await session.execute(text("RESET ROLE"))


async def enter_rls_subject(session: AsyncSession) -> None:
    await session.execute(text(f"SET LOCAL ROLE {RLS_TEST_ROLE}"))
