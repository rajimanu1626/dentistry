"""Schemas for sharing flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --------- internal share (doctor -> doctor) ---------


class PatientShareCreate(BaseModel):
    grantee_email: EmailStr
    role: str = Field(default="viewer", pattern=r"^(viewer|contributor)$")
    scope: dict[str, Any] = Field(default_factory=dict)
    expires_in_days: int = Field(default=30, ge=1, le=365)


class PatientSharePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    source_clinic_id: UUID
    grantee_user_id: UUID
    role: str
    scope: dict[str, Any]
    expires_at: datetime
    revoked_at: datetime | None
    created_by: UUID | None
    created_at: datetime


# --------- external share (link + password) ---------


class ExternalShareCreate(BaseModel):
    expires_in_seconds: int | None = Field(default=None, ge=60)
    max_views: int | None = Field(default=None, ge=1, le=50)
    recipient_label: str | None = Field(default=None, max_length=160)
    scope: dict[str, Any] = Field(default_factory=dict)
    password: str | None = Field(default=None, min_length=10, max_length=128)


class ExternalShareCreated(BaseModel):
    id: UUID
    url: str
    password: str
    expires_at: datetime
    max_views: int


class ExternalSharePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    clinic_id: UUID
    recipient_label: str | None
    expires_at: datetime
    revoked_at: datetime | None
    max_views: int
    view_count: int
    failed_attempts: int
    last_accessed_at: datetime | None
    created_by: UUID | None
    created_at: datetime


class ExternalUnlockRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ExternalUnlockResponse(BaseModel):
    share_session_token: str
    expires_in: int
    patient_summary: dict[str, Any]
