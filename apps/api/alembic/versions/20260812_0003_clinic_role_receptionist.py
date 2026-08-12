"""Add receptionist to clinic_role enum.

Revision ID: 0003_receptionist
Revises: 0002_system_role
Create Date: 2026-08-12 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_receptionist"
down_revision: str | None = "0002_system_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PG 16: ADD VALUE is fine inside a transaction; IF NOT EXISTS keeps re-runs safe.
    op.execute("ALTER TYPE clinic_role ADD VALUE IF NOT EXISTS 'receptionist'")


def downgrade() -> None:
    # Postgres cannot drop a single enum label safely while in use.
    pass
