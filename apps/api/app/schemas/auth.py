"""Auth request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import ClinicRole, SystemRole


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    invite_token: str | None = Field(default=None, min_length=16, max_length=256)
    clinic_name: str | None = Field(default=None, min_length=2, max_length=160)
    clinic_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9][a-z0-9\-]{1,79}$",
    )

    @model_validator(mode="after")
    def clinic_fields_pair(self) -> SignupRequest:
        has_name = self.clinic_name is not None
        has_slug = self.clinic_slug is not None
        if has_name != has_slug:
            raise ValueError("clinic_name and clinic_slug must be provided together.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token_type literal, not a secret
    expires_in: int


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None


class ClinicMembershipPublic(BaseModel):
    clinic_id: UUID
    clinic_slug: str
    clinic_name: str
    role: str


class MePublic(BaseModel):
    user: UserPublic
    memberships: list[ClinicMembershipPublic]
    system_role: SystemRole | None = None


class AuthConfigPublic(BaseModel):
    signup_mode: str
    can_signup: bool
    can_bootstrap_clinic: bool
    requires_invite: bool


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: ClinicRole = ClinicRole.DENTIST
    expires_in_seconds: int | None = Field(default=None, ge=3600, le=2_592_000)


class InviteCreated(BaseModel):
    invite_id: UUID
    email: EmailStr
    role: str
    invite_token: str
    expires_at: datetime


class InvitePublic(BaseModel):
    invite_id: UUID
    email: EmailStr
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)
