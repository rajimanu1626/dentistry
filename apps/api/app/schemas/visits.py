"""Schemas for visits and prescriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VisitCreate(BaseModel):
    patient_id: UUID
    visit_date: datetime
    dentist_id: UUID | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None
    treatment_plan: str | None = None
    notes: str | None = None


class VisitUpdate(BaseModel):
    visit_date: datetime | None = None
    dentist_id: UUID | None = None
    chief_complaint: str | None = None
    diagnosis: str | None = None
    treatment_plan: str | None = None
    notes: str | None = None


class VisitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    patient_id: UUID
    dentist_id: UUID | None
    visit_date: datetime
    chief_complaint: str | None
    diagnosis: str | None
    treatment_plan: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PrescriptionItem(BaseModel):
    medication: str = Field(min_length=1, max_length=120)
    dose: str = Field(min_length=1, max_length=60)
    frequency: str = Field(min_length=1, max_length=60)
    duration: str = Field(min_length=1, max_length=60)
    notes: str | None = Field(default=None, max_length=240)


class PrescriptionCreate(BaseModel):
    visit_id: UUID
    template_id: UUID | None = None
    items: list[PrescriptionItem]
    notes: str | None = None


class PrescriptionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    visit_id: UUID
    template_id: UUID | None
    items: list[dict[str, Any]]
    notes: str | None
    pdf_object_key: str | None
    created_at: datetime
    updated_at: datetime


class PrescriptionTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    html_template: str = Field(min_length=10)
    css: str | None = None
    is_default: bool = False


class PrescriptionTemplatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    name: str
    html_template: str
    css: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class VisitHistoryItem(BaseModel):
    id: UUID
    event_type: str
    event_time: datetime
    visit_id: UUID | None = None
    patient_id: UUID
    title: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisitHistoryPage(BaseModel):
    items: list[VisitHistoryItem]
    next_cursor: str | None = None


class VisitSummaryPublic(BaseModel):
    visit: VisitPublic
    prescriptions: list[PrescriptionPublic]
    media: list[dict[str, Any]]
