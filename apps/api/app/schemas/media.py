"""Schemas for patient media."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientMediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    visit_id: UUID | None
    kind: str
    mime_type: str
    width_px: int | None
    height_px: int | None
    bytes_size: int | None
    object_key: str
    created_at: datetime


class PatientMediaWithUrl(PatientMediaPublic):
    signed_url: str
