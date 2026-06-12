"""Initial schema: tables + ENUMs + RLS policies + audit triggers.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27 23:00:00+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, INET, JSONB, UUID

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --------------------------------------------------------------------------- #
# Helper: tables that need RLS + audit triggers
# --------------------------------------------------------------------------- #
TENANT_TABLES = (
    "clinics",
    "clinic_members",
    "clinic_invites",
    "patients",
    "visits",
    "prescriptions",
    "prescription_templates",
    "patient_media",
    "patient_shares",
    "external_share_links",
)

AUDITED_TABLES = (
    "patients",
    "visits",
    "prescriptions",
    "patient_media",
    "patient_shares",
    "external_share_links",
    "clinic_members",
)


# --------------------------------------------------------------------------- #
# Upgrade
# --------------------------------------------------------------------------- #


def upgrade() -> None:
    # Extensions (idempotent — already created by infra/db/init in dev but tests
    # spin up a bare Postgres so we re-create them here).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # ENUMs
    op.execute("CREATE TYPE clinic_role AS ENUM ('owner','dentist','assistant','front_desk');")
    op.execute("CREATE TYPE media_kind AS ENUM ('before','after','xray','other');")
    op.execute("CREATE TYPE share_role AS ENUM ('viewer','contributor');")
    op.execute(
        "CREATE TYPE audit_action AS ENUM ("
        "'insert','update','delete','login','logout','login_failed','pdf_export',"
        "'external_share_created','external_share_viewed','external_share_failed_unlock','external_share_revoked',"
        "'patient_share_created','patient_share_revoked'"
        ");"
    )

    # ---- users (identity-provider mirror) ----
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", CITEXT(), nullable=False, unique=True),
        sa.Column("full_name", sa.String(160)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ---- clinic_groups ----
    op.create_table(
        "clinic_groups",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column(
            "owner_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ---- clinics ----
    op.create_table(
        "clinics",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "group_id", UUID(as_uuid=True), sa.ForeignKey("clinic_groups.id", ondelete="SET NULL")
        ),
        sa.Column("slug", CITEXT(), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "patient_code_prefix", sa.String(8), nullable=False, server_default=sa.text("'DC'")
        ),
        sa.Column(
            "patient_code_sequence", sa.BigInteger, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ---- clinic_members ----
    op.create_table(
        "clinic_members",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            ENUM(
                "owner", "dentist", "assistant", "front_desk", name="clinic_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("clinic_id", "user_id", name="uq_clinic_members_clinic_user"),
    )
    op.create_index("ix_clinic_members_user", "clinic_members", ["user_id"])

    # ---- clinic_invites ----
    op.create_table(
        "clinic_invites",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", CITEXT(), nullable=False),
        sa.Column(
            "role",
            ENUM(
                "owner", "dentist", "assistant", "front_desk", name="clinic_role", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("token_hmac", sa.LargeBinary, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("clinic_id", "email", name="uq_clinic_invites_clinic_email"),
    )

    # ---- patients ----
    op.create_table(
        "patients",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("patient_code", sa.String(32), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("sex", sa.String(16)),
        sa.Column("phone_enc", sa.LargeBinary),
        sa.Column("email", CITEXT()),
        sa.Column("address_enc", sa.LargeBinary),
        sa.Column("allergies_enc", sa.LargeBinary),
        sa.Column("medical_history_enc", sa.LargeBinary),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("clinic_id", "patient_code", name="uq_patients_clinic_code"),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])
    op.create_index("ix_patients_clinic_name", "patients", ["clinic_id", "full_name"])
    op.execute("CREATE INDEX ix_patients_name_trgm ON patients USING gin (full_name gin_trgm_ops);")

    # ---- visits ----
    op.create_table(
        "visits",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dentist_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("visit_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chief_complaint", sa.Text),
        sa.Column("diagnosis", sa.Text),
        sa.Column("treatment_plan", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_visits_patient_date", "visits", ["patient_id", "visit_date"])
    op.create_index("ix_visits_clinic_date", "visits", ["clinic_id", "visit_date"])

    # ---- prescription_templates ----
    op.create_table(
        "prescription_templates",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("html_template", sa.Text, nullable=False),
        sa.Column("css", sa.Text),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("clinic_id", "name", name="uq_prescription_templates_clinic_name"),
    )

    # ---- prescriptions ----
    op.create_table(
        "prescriptions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "visit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("visits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("prescription_templates.id", ondelete="SET NULL"),
        ),
        sa.Column("items", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("notes", sa.Text),
        sa.Column("pdf_object_key", sa.String(512)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prescriptions_visit", "prescriptions", ["visit_id"])

    # ---- patient_media ----
    op.create_table(
        "patient_media",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("visit_id", UUID(as_uuid=True), sa.ForeignKey("visits.id", ondelete="SET NULL")),
        sa.Column(
            "kind",
            ENUM("before", "after", "xray", "other", name="media_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("width_px", sa.Integer),
        sa.Column("height_px", sa.Integer),
        sa.Column("bytes_size", sa.BigInteger),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column(
            "uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_patient_media_patient", "patient_media", ["patient_id"])
    op.create_index("ix_patient_media_visit", "patient_media", ["visit_id"])

    # ---- patient_shares ----
    op.create_table(
        "patient_shares",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grantee_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            ENUM("viewer", "contributor", name="share_role", create_type=False),
            nullable=False,
        ),
        sa.Column("scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_patient_shares_grantee", "patient_shares", ["grantee_user_id"])
    op.create_index("ix_patient_shares_patient", "patient_shares", ["patient_id"])

    # ---- external_share_links ----
    op.create_table(
        "external_share_links",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "clinic_id",
            UUID(as_uuid=True),
            sa.ForeignKey("clinics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hmac", sa.LargeBinary, nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("max_views", sa.Integer, nullable=False, server_default=sa.text("5")),
        sa.Column("view_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("failed_attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.Column("last_accessed_ip", INET),
        sa.Column("recipient_label", sa.String(160)),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_external_share_links_patient", "external_share_links", ["patient_id"])

    # ---- audit_log ----
    op.create_table(
        "audit_log",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "clinic_id", UUID(as_uuid=True), sa.ForeignKey("clinics.id", ondelete="SET NULL")
        ),
        sa.Column(
            "actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column(
            "action",
            ENUM(
                "insert",
                "update",
                "delete",
                "login",
                "logout",
                "login_failed",
                "pdf_export",
                "external_share_created",
                "external_share_viewed",
                "external_share_failed_unlock",
                "external_share_revoked",
                "patient_share_created",
                "patient_share_revoked",
                name="audit_action",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("entity", sa.String(80), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True)),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip", INET),
        sa.Column("user_agent", sa.String(512)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"])
    op.create_index("ix_audit_log_actor_ts", "audit_log", ["actor_user_id", "created_at"])
    op.create_index("ix_audit_log_clinic_ts", "audit_log", ["clinic_id", "created_at"])

    # ----------------------------------------------------------------------- #
    # Audit trigger function
    # ----------------------------------------------------------------------- #
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_row_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_actor uuid;
            v_clinic uuid;
            v_entity text := TG_TABLE_NAME;
            v_id uuid;
            v_payload jsonb := '{}'::jsonb;
            v_action audit_action;
        BEGIN
            BEGIN
            v_actor := (
                SELECT u.id
                FROM users u
                WHERE u.id = nullif(current_setting('app.current_user_id', true), '')::uuid
            );
            EXCEPTION WHEN OTHERS THEN
                v_actor := NULL;
            END;

            IF TG_OP = 'INSERT' THEN
                v_action := 'insert';
                v_id := NEW.id;
                v_payload := to_jsonb(NEW) - 'phone_enc' - 'allergies_enc'
                             - 'address_enc' - 'medical_history_enc' - 'password_hash' - 'token_hmac';
                v_clinic := COALESCE(
                    NULLIF(to_jsonb(NEW)->>'clinic_id', '')::uuid,
                    NULLIF(to_jsonb(NEW)->>'source_clinic_id', '')::uuid
                );
            ELSIF TG_OP = 'UPDATE' THEN
                v_action := 'update';
                v_id := NEW.id;
                v_payload := jsonb_build_object(
                    'before', to_jsonb(OLD) - 'phone_enc' - 'allergies_enc'
                              - 'address_enc' - 'medical_history_enc' - 'password_hash' - 'token_hmac',
                    'after',  to_jsonb(NEW) - 'phone_enc' - 'allergies_enc'
                              - 'address_enc' - 'medical_history_enc' - 'password_hash' - 'token_hmac'
                );
                v_clinic := COALESCE(
                    NULLIF(to_jsonb(NEW)->>'clinic_id', '')::uuid,
                    NULLIF(to_jsonb(NEW)->>'source_clinic_id', '')::uuid
                );
            ELSE
                v_action := 'delete';
                v_id := OLD.id;
                v_payload := to_jsonb(OLD) - 'phone_enc' - 'allergies_enc'
                             - 'address_enc' - 'medical_history_enc' - 'password_hash' - 'token_hmac';
                v_clinic := COALESCE(
                    NULLIF(to_jsonb(OLD)->>'clinic_id', '')::uuid,
                    NULLIF(to_jsonb(OLD)->>'source_clinic_id', '')::uuid
                );
            END IF;

            INSERT INTO audit_log (clinic_id, actor_user_id, action, entity, entity_id, payload)
            VALUES (v_clinic, v_actor, v_action, v_entity, v_id, v_payload);

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    for tbl in AUDITED_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER audit_{tbl}
            AFTER INSERT OR UPDATE OR DELETE ON {tbl}
            FOR EACH ROW EXECUTE FUNCTION audit_row_change();
            """
        )

    # ----------------------------------------------------------------------- #
    # patient_code generator: trigger on INSERT auto-assigns DC-YYYY-NNNNN
    # if blank, using a per-clinic sequence stored on the clinics row.
    # ----------------------------------------------------------------------- #
    op.execute(
        """
        CREATE OR REPLACE FUNCTION assign_patient_code() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            v_seq bigint;
            v_prefix text;
            v_year text := to_char(now() AT TIME ZONE 'UTC', 'YYYY');
        BEGIN
            IF NEW.patient_code IS NOT NULL AND NEW.patient_code <> '' THEN
                RETURN NEW;
            END IF;

            UPDATE clinics
            SET patient_code_sequence = patient_code_sequence + 1
            WHERE id = NEW.clinic_id
            RETURNING patient_code_sequence, patient_code_prefix
            INTO v_seq, v_prefix;

            IF v_seq IS NULL THEN
                RAISE EXCEPTION 'Unknown clinic % when generating patient_code', NEW.clinic_id;
            END IF;

            NEW.patient_code := v_prefix || '-' || v_year || '-' || lpad(v_seq::text, 5, '0');
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_patient_code
        BEFORE INSERT ON patients
        FOR EACH ROW EXECUTE FUNCTION assign_patient_code();
        """
    )

    # ----------------------------------------------------------------------- #
    # Row-Level Security
    # ----------------------------------------------------------------------- #
    # Portability note: policies use current_setting('app.current_user_id') so
    # they remain valid on plain RDS / Cognito without modification.
    for tbl in TENANT_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")

    # Helper SQL: a CTE that resolves the caller's clinic memberships.
    membership_cte = (
        "SELECT clinic_id FROM clinic_members "
        "WHERE user_id = nullif(current_setting('app.current_user_id', true), '')::uuid"
    )
    share_clause = (
        "EXISTS (SELECT 1 FROM patient_shares ps "
        "WHERE ps.patient_id = patients.id "
        "AND ps.grantee_user_id = nullif(current_setting('app.current_user_id', true), '')::uuid "
        "AND ps.revoked_at IS NULL AND ps.expires_at > now())"
    )

    # clinics: a user sees a clinic if they are a member.
    op.execute(
        f"""
        CREATE POLICY p_clinics_select ON clinics FOR SELECT
        USING (id IN ({membership_cte}));
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_clinics_modify ON clinics FOR ALL
        USING (id IN ({membership_cte}))
        WITH CHECK (id IN ({membership_cte}));
        """
    )

    # clinic_members: visible if the row's clinic is in your membership set.
    for table in ("clinic_members", "clinic_invites", "prescription_templates"):
        op.execute(
            f"""
            CREATE POLICY p_{table}_all ON {table} FOR ALL
            USING (clinic_id IN ({membership_cte}))
            WITH CHECK (clinic_id IN ({membership_cte}));
            """
        )

    # patients: member of clinic OR has an active patient_share.
    op.execute(
        f"""
        CREATE POLICY p_patients_select ON patients FOR SELECT
        USING (clinic_id IN ({membership_cte}) OR {share_clause});
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_patients_modify ON patients FOR ALL
        USING (clinic_id IN ({membership_cte}))
        WITH CHECK (clinic_id IN ({membership_cte}));
        """
    )

    # child tables inherit the parent patient's visibility (FK -> patients)
    for child in ("visits", "patient_media"):
        op.execute(
            f"""
            CREATE POLICY p_{child}_select ON {child} FOR SELECT
            USING (
                clinic_id IN ({membership_cte})
                OR EXISTS (
                    SELECT 1 FROM patient_shares ps
                    WHERE ps.patient_id = {child}.patient_id
                      AND ps.grantee_user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
                      AND ps.revoked_at IS NULL AND ps.expires_at > now()
                )
            );
            """
        )
        op.execute(
            f"""
            CREATE POLICY p_{child}_modify ON {child} FOR INSERT
            WITH CHECK (clinic_id IN ({membership_cte}));
            """
        )
        op.execute(
            f"""
            CREATE POLICY p_{child}_update ON {child} FOR UPDATE
            USING (clinic_id IN ({membership_cte}))
            WITH CHECK (clinic_id IN ({membership_cte}));
            """
        )
        op.execute(
            f"""
            CREATE POLICY p_{child}_delete ON {child} FOR DELETE
            USING (clinic_id IN ({membership_cte}));
            """
        )

    # prescriptions link through visits -> patients, so sharing checks patient via visit.
    op.execute(
        f"""
        CREATE POLICY p_prescriptions_select ON prescriptions FOR SELECT
        USING (
            clinic_id IN ({membership_cte})
            OR EXISTS (
                SELECT 1
                FROM patient_shares ps
                JOIN visits v ON v.patient_id = ps.patient_id
                WHERE v.id = prescriptions.visit_id
                  AND ps.grantee_user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
                  AND ps.revoked_at IS NULL
                  AND ps.expires_at > now()
            )
        );
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_prescriptions_modify ON prescriptions FOR INSERT
        WITH CHECK (clinic_id IN ({membership_cte}));
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_prescriptions_update ON prescriptions FOR UPDATE
        USING (clinic_id IN ({membership_cte}))
        WITH CHECK (clinic_id IN ({membership_cte}));
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_prescriptions_delete ON prescriptions FOR DELETE
        USING (clinic_id IN ({membership_cte}));
        """
    )

    # patient_shares: owners (members of source_clinic_id) and the grantee can see.
    op.execute(
        f"""
        CREATE POLICY p_patient_shares_select ON patient_shares FOR SELECT
        USING (
            source_clinic_id IN ({membership_cte})
            OR grantee_user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
        );
        """
    )
    op.execute(
        f"""
        CREATE POLICY p_patient_shares_modify ON patient_shares FOR ALL
        USING (source_clinic_id IN ({membership_cte}))
        WITH CHECK (source_clinic_id IN ({membership_cte}));
        """
    )

    # external_share_links: only clinic members manage them.
    op.execute(
        f"""
        CREATE POLICY p_external_share_links_all ON external_share_links FOR ALL
        USING (clinic_id IN ({membership_cte}))
        WITH CHECK (clinic_id IN ({membership_cte}));
        """
    )

    # Grants — app role has full CRUD on app tables (RLS is the gate, not GRANT).
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
            END IF;
        END $$;
        """
    )


# --------------------------------------------------------------------------- #
# Downgrade
# --------------------------------------------------------------------------- #


def downgrade() -> None:
    # Triggers + functions
    for tbl in AUDITED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS audit_{tbl} ON {tbl};")
    op.execute("DROP TRIGGER IF EXISTS set_patient_code ON patients;")
    op.execute("DROP FUNCTION IF EXISTS audit_row_change();")
    op.execute("DROP FUNCTION IF EXISTS assign_patient_code();")

    # Drop tables in FK-safe order
    for table in (
        "audit_log",
        "external_share_links",
        "patient_shares",
        "patient_media",
        "prescriptions",
        "prescription_templates",
        "visits",
        "patients",
        "clinic_invites",
        "clinic_members",
        "clinics",
        "clinic_groups",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    # ENUMs
    for type_name in ("audit_action", "share_role", "media_kind", "clinic_role"):
        op.execute(f"DROP TYPE IF EXISTS {type_name};")
