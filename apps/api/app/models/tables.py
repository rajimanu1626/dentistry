"""ORM tables.

Every tenant-scoped table carries a ``clinic_id`` so RLS policies (defined in
the initial Alembic migration) can isolate clinics. PHI fields like ``phone``
and ``allergies`` are stored as ``bytea`` (pgp_sym_encrypt outputs) so the at-rest
representation is encrypted with ``PHI_ENCRYPTION_KEY``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import CreatedAt, UpdatedAt, UUIDColumn, UUIDPk
from app.models.enums import AuditAction, ClinicRole, MediaKind, ShareRole, SystemRole

# Postgres ENUM definitions (created in the initial migration).
clinic_role_enum = ENUM(
    *(r.value for r in ClinicRole),
    name="clinic_role",
    create_type=False,
)
system_role_enum = ENUM(
    *(r.value for r in SystemRole),
    name="system_role",
    create_type=False,
)
media_kind_enum = ENUM(
    *(k.value for k in MediaKind),
    name="media_kind",
    create_type=False,
)
share_role_enum = ENUM(
    *(r.value for r in ShareRole),
    name="share_role",
    create_type=False,
)
audit_action_enum = ENUM(
    *(a.value for a in AuditAction),
    name="audit_action",
    create_type=False,
)


# --------------------------------------------------------------------------- #
# Identity & tenancy
# --------------------------------------------------------------------------- #


class ClinicGroup(Base):
    """A chain / parent organisation owning multiple clinics."""

    __tablename__ = "clinic_groups"

    id: Mapped[UUIDPk]
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    clinics: Mapped[list[Clinic]] = relationship(back_populates="group")


class User(Base):
    """Local mirror of the identity-provider user.

    Provider-agnostic: ``id`` matches the JWT ``sub`` claim regardless of whether
    Supabase Auth, Cognito or Keycloak issued it. No FK targets ``auth.users``.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(160))
    system_role: Mapped[SystemRole | None] = mapped_column(system_role_enum, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    memberships: Mapped[list[ClinicMember]] = relationship(back_populates="user")


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[UUIDPk]
    group_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinic_groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    patient_code_prefix: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default=text("'DC'")
    )
    patient_code_sequence: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    group: Mapped[ClinicGroup | None] = relationship(back_populates="clinics")
    members: Mapped[list[ClinicMember]] = relationship(back_populates="clinic")
    patients: Mapped[list[Patient]] = relationship(back_populates="clinic")


class ClinicMember(Base):
    __tablename__ = "clinic_members"
    __table_args__ = (
        UniqueConstraint("clinic_id", "user_id", name="uq_clinic_members_clinic_user"),
        Index("ix_clinic_members_user", "user_id"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ClinicRole] = mapped_column(clinic_role_enum, nullable=False)
    created_at: Mapped[CreatedAt]

    clinic: Mapped[Clinic] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class ClinicInvite(Base):
    __tablename__ = "clinic_invites"
    __table_args__ = (
        UniqueConstraint("clinic_id", "email", name="uq_clinic_invites_clinic_email"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    role: Mapped[ClinicRole] = mapped_column(clinic_role_enum, nullable=False)
    invited_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    token_hmac: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]


# --------------------------------------------------------------------------- #
# Clinical
# --------------------------------------------------------------------------- #


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "patient_code", name="uq_patients_clinic_code"),
        Index("ix_patients_clinic_name", "clinic_id", "full_name"),
        Index(
            "ix_patients_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_code: Mapped[str] = mapped_column(String(32), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(16))
    phone_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    email: Mapped[str | None] = mapped_column(CITEXT())
    address_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    allergies_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    medical_history_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    clinic: Mapped[Clinic] = relationship(back_populates="patients")
    visits: Mapped[list[Visit]] = relationship(back_populates="patient")


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        Index("ix_visits_patient_date", "patient_id", "visit_date"),
        Index("ix_visits_clinic_date", "clinic_id", "visit_date"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    dentist_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    patient: Mapped[Patient] = relationship(back_populates="visits")
    prescriptions: Mapped[list[Prescription]] = relationship(back_populates="visit")


class PrescriptionTemplate(Base):
    __tablename__ = "prescription_templates"
    __table_args__ = (
        UniqueConstraint("clinic_id", "name", name="uq_prescription_templates_clinic_name"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    html_template: Mapped[str] = mapped_column(Text, nullable=False)
    css: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]


class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = (Index("ix_prescriptions_visit", "visit_id"),)

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    visit_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("prescription_templates.id", ondelete="SET NULL"),
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    pdf_object_key: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]

    visit: Mapped[Visit] = relationship(back_populates="prescriptions")


class PatientMedia(Base):
    __tablename__ = "patient_media"
    __table_args__ = (
        Index("ix_patient_media_patient", "patient_id"),
        Index("ix_patient_media_visit", "visit_id"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    visit_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL")
    )
    kind: Mapped[MediaKind] = mapped_column(media_kind_enum, nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    bytes_size: Mapped[int | None] = mapped_column(BigInteger)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[CreatedAt]


# --------------------------------------------------------------------------- #
# Sharing
# --------------------------------------------------------------------------- #


class PatientShare(Base):
    __tablename__ = "patient_shares"
    __table_args__ = (
        Index("ix_patient_shares_grantee", "grantee_user_id"),
        Index("ix_patient_shares_patient", "patient_id"),
    )

    id: Mapped[UUIDPk]
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    grantee_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ShareRole] = mapped_column(share_role_enum, nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[CreatedAt]


class ExternalShareLink(Base):
    __tablename__ = "external_share_links"
    __table_args__ = (Index("ix_external_share_links_patient", "patient_id"),)

    id: Mapped[UUIDPk]
    patient_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hmac: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_views: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("5"))
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_ip: Mapped[str | None] = mapped_column(INET)
    recipient_label: Mapped[str | None] = mapped_column(String(160))
    created_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[CreatedAt]


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity", "entity_id"),
        Index("ix_audit_log_actor_ts", "actor_user_id", "created_at"),
        Index("ix_audit_log_clinic_ts", "clinic_id", "created_at"),
    )

    id: Mapped[UUIDPk]
    clinic_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clinics.id", ondelete="SET NULL"),
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    action: Mapped[AuditAction] = mapped_column(audit_action_enum, nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[CreatedAt]


__all__ = [
    "AuditLog",
    "Clinic",
    "ClinicGroup",
    "ClinicInvite",
    "ClinicMember",
    "ExternalShareLink",
    "Patient",
    "PatientMedia",
    "PatientShare",
    "Prescription",
    "PrescriptionTemplate",
    "User",
    "Visit",
]

# silence unused import warnings (JSON kept for future fields)
_ = JSON
_ = UUIDColumn
