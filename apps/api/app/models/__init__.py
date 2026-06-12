"""SQLAlchemy ORM models for clinic-crm.

Importing this module registers every table on :class:`app.db.base.Base.metadata`
which is what Alembic introspects for autogenerate.
"""

from app.models.enums import (
    AuditAction,
    ClinicRole,
    MediaKind,
    ShareRole,
    ShareStatus,
    SystemRole,
)
from app.models.tables import (
    AuditLog,
    Clinic,
    ClinicGroup,
    ClinicInvite,
    ClinicMember,
    ExternalShareLink,
    Patient,
    PatientMedia,
    PatientShare,
    Prescription,
    PrescriptionTemplate,
    User,
    Visit,
)

__all__ = [
    "AuditAction",
    "AuditLog",
    "Clinic",
    "ClinicGroup",
    "ClinicInvite",
    "ClinicMember",
    "ClinicRole",
    "ExternalShareLink",
    "MediaKind",
    "Patient",
    "PatientMedia",
    "PatientShare",
    "Prescription",
    "PrescriptionTemplate",
    "ShareRole",
    "ShareStatus",
    "SystemRole",
    "User",
    "Visit",
]
