"""Platform operator schemas (no PHI)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ClinicRole, SystemRole


class PlatformGroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    owner_user_id: UUID


class PlatformGroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime


class PlatformClinicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9\-]{1,79}$")
    group_id: UUID | None = None
    address: str | None = None


class PlatformClinicPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    group_id: UUID | None
    address: str | None
    created_at: datetime


class PlatformUserPublic(BaseModel):
    id: UUID
    # Plain str: dev accounts use .test emails that strict EmailStr rejects.
    email: str
    full_name: str | None
    is_active: bool
    system_role: SystemRole | None
    created_at: datetime


class PlatformUserUpdate(BaseModel):
    is_active: bool | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)


class PlatformClinicInviteCreate(BaseModel):
    email: EmailStr
    role: ClinicRole = ClinicRole.OWNER
    expires_in_seconds: int | None = Field(default=None, ge=3600, le=2_592_000)
