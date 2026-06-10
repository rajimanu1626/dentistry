"""Add users.system_role for platform operators.

Revision ID: 0002_system_role
Revises: 0001_initial
Create Date: 2026-06-03 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "0002_system_role"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

system_role = ENUM(
    "platform_admin",
    "platform_support",
    name="system_role",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE system_role AS ENUM ('platform_admin', 'platform_support');"
    )
    op.add_column(
        "users",
        sa.Column("system_role", system_role, nullable=True),
    )
    op.create_index("ix_users_system_role", "users", ["system_role"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_system_role", table_name="users")
    op.drop_column("users", "system_role")
    op.execute("DROP TYPE system_role;")
