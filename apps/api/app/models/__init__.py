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
    enum_str,
)
from app.models.tables import (
    AuditLog,
    Clinic,
    ClinicGroup,
    ClinicInfraCost,
    ClinicInvite,
    ClinicMember,
    ClinicPlanAssignment,
    ClinicUsageSnapshot,
    ExternalShareLink,
    Patient,
    PatientMedia,
    PatientShare,
    Prescription,
    PrescriptionTemplate,
    UsageEvent,
    UsagePlan,
    User,
    Visit,
)

__all__ = [
    "AuditAction",
    "AuditLog",
    "Clinic",
    "ClinicGroup",
    "ClinicInfraCost",
    "ClinicInvite",
    "ClinicMember",
    "ClinicPlanAssignment",
    "ClinicRole",
    "ClinicUsageSnapshot",
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
    "UsageEvent",
    "UsagePlan",
    "User",
    "Visit",
    "enum_str",
]
