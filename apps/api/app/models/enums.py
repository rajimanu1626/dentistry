"""Enumerations shared across models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


def enum_str(value: Any) -> str:
    """Normalize SQLAlchemy enum / StrEnum / plain str to a string value."""
    if value is None:
        return ""
    raw = getattr(value, "value", value)
    return str(raw)


class ClinicRole(StrEnum):
    OWNER = "owner"
    DENTIST = "dentist"
    ASSISTANT = "assistant"
    FRONT_DESK = "front_desk"
    RECEPTIONIST = "receptionist"


# Roles allowed to register / update patient demographics.
PATIENT_WRITE_ROLES: tuple[ClinicRole, ...] = (
    ClinicRole.OWNER,
    ClinicRole.DENTIST,
    ClinicRole.ASSISTANT,
    ClinicRole.FRONT_DESK,
    ClinicRole.RECEPTIONIST,
)


class SystemRole(StrEnum):
    """Platform operators manage orgs/clinics/users; no clinical PHI access."""

    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_SUPPORT = "platform_support"


class MediaKind(StrEnum):
    BEFORE = "before"
    AFTER = "after"
    XRAY = "xray"
    OTHER = "other"


class ShareRole(StrEnum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"


class ShareStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuditAction(StrEnum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PDF_EXPORT = "pdf_export"
    EXTERNAL_SHARE_CREATED = "external_share_created"
    EXTERNAL_SHARE_VIEWED = "external_share_viewed"
    EXTERNAL_SHARE_FAILED_UNLOCK = "external_share_failed_unlock"
    EXTERNAL_SHARE_REVOKED = "external_share_revoked"
    PATIENT_SHARE_CREATED = "patient_share_created"
    PATIENT_SHARE_REVOKED = "patient_share_revoked"
