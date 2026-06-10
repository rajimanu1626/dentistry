"""Enumerations shared across models."""

from __future__ import annotations

from enum import StrEnum


class ClinicRole(StrEnum):
    OWNER = "owner"
    DENTIST = "dentist"
    ASSISTANT = "assistant"
    FRONT_DESK = "front_desk"


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
