"""Spin up a real Postgres via testcontainers + apply Alembic migrations."""

from __future__ import annotations

import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        import docker  # type: ignore[import-untyped]

        docker.from_env().ping()
    except Exception:
        return False
    return True


pytestmark_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker is not available; testcontainers-based tests are skipped.",
)


def _async_url(sync_url: str) -> str:
    """Convert ``postgresql+psycopg2://`` -> ``postgresql+asyncpg://``."""
    parsed = urlparse(sync_url)
    scheme = "postgresql+asyncpg"
    return urlunparse(parsed._replace(scheme=scheme))


def _alembic_url(sync_url: str) -> str:
    """Force psycopg driver for Alembic (sync)."""
    parsed = urlparse(sync_url)
    scheme = "postgresql+psycopg"
    return urlunparse(parsed._replace(scheme=scheme))


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    if not _docker_available():
        pytest.skip("Docker is not available; testcontainers-based tests are skipped.")
    container = PostgresContainer(image="postgres:16-alpine", driver=None)
    with container:
        yield container


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    return _async_url(postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def database_url_sync(postgres_container: PostgresContainer) -> str:
    return _alembic_url(postgres_container.get_connection_url())


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(database_url: str, database_url_sync: str) -> None:
    """Run Alembic against the container once per test session."""
    os.environ["DATABASE_URL"] = database_url
    os.environ["DATABASE_URL_SYNC"] = database_url_sync

    from app.core.config import get_settings

    get_settings.cache_clear()

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url_sync)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    """One fresh session per test, with all tables truncated."""
    engine = create_async_engine(database_url, future=True)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as cleanup:
        await cleanup.execute(
            text(
                "TRUNCATE TABLE audit_log, external_share_links, patient_shares, "
                "patient_media, prescriptions, prescription_templates, visits, "
                "patients, clinic_invites, clinic_members, clinics, clinic_groups, "
                "users RESTART IDENTITY CASCADE;"
            )
        )
        await cleanup.commit()

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(
    database_url: str,
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    """HTTP client against the app wired to the testcontainers Postgres."""
    os.environ["DATABASE_URL"] = database_url
    os.environ["IDENTITY_PROVIDER"] = "local"
    os.environ["SIGNUP_MODE"] = "invite"
    os.environ["APP_ENV"] = "test"

    from app.core.config import get_settings
    from app.db.session import reset_engine
    from app.main import create_app

    get_settings.cache_clear()
    await reset_engine()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    get_settings.cache_clear()
    await reset_engine()
