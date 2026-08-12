"""Platform usage analytics tables.

Revision ID: 0005_platform_usage
Revises: 0004_clinic_members_rls
Create Date: 2026-08-12 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_platform_usage"
down_revision: str | None = "0004_clinic_members_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEMBERSHIP_CTE = (
    "SELECT clinic_id FROM clinic_members "
    "WHERE user_id = nullif(current_setting('app.current_user_id', true), '')::uuid"
)

TENANT_USAGE_TABLES = (
    "clinic_plan_assignments",
    "clinic_usage_snapshots",
    "usage_events",
    "clinic_infra_costs",
)


def upgrade() -> None:
    op.create_table(
        "usage_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("included_media_bytes", sa.BigInteger(), nullable=False),
        sa.Column("included_db_bytes", sa.BigInteger(), nullable=False),
        sa.Column("max_members", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "clinic_plan_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usage_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_clinic_plan_assignments_clinic", "clinic_plan_assignments", ["clinic_id"])
    op.create_index("ix_clinic_plan_assignments_plan", "clinic_plan_assignments", ["plan_id"])

    op.create_table(
        "clinic_usage_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("media_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("media_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("patients_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("visits_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("prescriptions_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("members_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("audit_rows_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_external_shares_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("db_bytes_estimated", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("s3_bytes_reconciled", sa.BigInteger(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("clinic_id", "snapshot_date", name="uq_clinic_usage_snapshots_day"),
    )
    op.create_index(
        "ix_clinic_usage_snapshots_clinic_date",
        "clinic_usage_snapshots",
        ["clinic_id", "snapshot_date"],
    )

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_usage_events_clinic_ts", "usage_events", ["clinic_id", "created_at"])
    op.create_index("ix_usage_events_type", "usage_events", ["event_type"])

    op.create_table(
        "clinic_infra_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("cost_paise", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(64), server_default=sa.text("'manual'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_clinic_infra_costs_clinic_period",
        "clinic_infra_costs",
        ["clinic_id", "period_start"],
    )

    for tbl in TENANT_USAGE_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY p_{tbl}_all ON {tbl} FOR ALL
            USING (clinic_id IN ({MEMBERSHIP_CTE}))
            WITH CHECK (clinic_id IN ({MEMBERSHIP_CTE}));
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER audit_{tbl}
            AFTER INSERT OR UPDATE OR DELETE ON {tbl}
            FOR EACH ROW EXECUTE FUNCTION audit_row_change();
            """
        )

    op.execute(
        """
        INSERT INTO usage_plans (id, name, included_media_bytes, included_db_bytes, max_members)
        VALUES (
            gen_random_uuid(),
            'Starter',
            5368709120,
            268435456,
            10
        );
        """
    )


def downgrade() -> None:
    for tbl in reversed(TENANT_USAGE_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS audit_{tbl} ON {tbl};")
        op.execute(f"DROP POLICY IF EXISTS p_{tbl}_all ON {tbl};")
    op.drop_table("clinic_infra_costs")
    op.drop_table("usage_events")
    op.drop_table("clinic_usage_snapshots")
    op.drop_table("clinic_plan_assignments")
    op.drop_table("usage_plans")
