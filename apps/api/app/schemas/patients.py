"""Patient request/response schemas. PHI is decrypted by the service layer
*after* the row has passed RLS, never on the wire."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=16)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    address: str | None = None
    allergies: str | None = None
    medical_history: str | None = None
    notes: str | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=16)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    address: str | None = None
    allergies: str | None = None
    medical_history: str | None = None
    notes: str | None = None


class PatientPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    patient_code: str
    full_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    email: str | None
    address: str | None
    allergies: str | None
    medical_history: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PatientListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_code: str
    full_name: str
    date_of_birth: date | None
    sex: str | None
    created_at: datetime


class PatientPage(BaseModel):
    items: list[PatientListItem]
    total: int
    page: int
    page_size: int
