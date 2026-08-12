"""Fix clinic_members RLS recursion for non-superuser roles.

Revision ID: 0004_clinic_members_rls
Revises: 0003_receptionist
Create Date: 2026-08-12 00:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_clinic_members_rls"
down_revision: str | None = "0003_receptionist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The old policy referenced clinic_members inside a subquery on clinic_members,
    # which Postgres rejects once RLS is enforced for non-superuser roles.
    op.execute("DROP POLICY IF EXISTS p_clinic_members_all ON clinic_members;")
    op.execute(
        """
        CREATE POLICY p_clinic_members_all ON clinic_members FOR ALL
        USING (
            user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
            OR clinic_id = nullif(current_setting('app.current_clinic_id', true), '')::uuid
        )
        WITH CHECK (
            clinic_id = nullif(current_setting('app.current_clinic_id', true), '')::uuid
            OR user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS p_clinic_members_all ON clinic_members;")
    op.execute(
        """
        CREATE POLICY p_clinic_members_all ON clinic_members FOR ALL
        USING (
            clinic_id IN (
                SELECT clinic_id FROM clinic_members
                WHERE user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
            )
        )
        WITH CHECK (
            clinic_id IN (
                SELECT clinic_id FROM clinic_members
                WHERE user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
            )
        );
        """
    )
