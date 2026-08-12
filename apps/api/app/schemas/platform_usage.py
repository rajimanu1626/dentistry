"""Platform usage analytics schemas (no PHI)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UsageStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    OVER_LIMIT = "over_limit"


class MediaKindBreakdown(BaseModel):
    kind: str
    count: int
    bytes: int


class ClinicUsageMetrics(BaseModel):
    clinic_id: UUID
    clinic_name: str
    clinic_slug: str
    media_bytes: int = 0
    media_count: int = 0
    patients_count: int = 0
    visits_count: int = 0
    prescriptions_count: int = 0
    members_count: int = 0
    audit_rows_count: int = 0
    active_external_shares_count: int = 0
    db_bytes_estimated: int = 0
    s3_bytes_reconciled: int | None = None
    plan_id: UUID | None = None
    plan_name: str | None = None
    included_media_bytes: int | None = None
    included_db_bytes: int | None = None
    media_usage_pct: float | None = None
    db_usage_pct: float | None = None
    status: UsageStatus = UsageStatus.OK


class ClinicUsageDetail(ClinicUsageMetrics):
    media_by_kind: list[MediaKindBreakdown] = Field(default_factory=list)
    usage_events_30d: dict[str, int] = Field(default_factory=dict)


class ClinicUsagePage(BaseModel):
    items: list[ClinicUsageMetrics]
    total: int
    page: int
    page_size: int


class ClinicUsageSnapshotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date
    media_bytes: int
    media_count: int
    patients_count: int
    visits_count: int
    prescriptions_count: int
    members_count: int
    audit_rows_count: int
    active_external_shares_count: int
    db_bytes_estimated: int
    s3_bytes_reconciled: int | None
    computed_at: datetime


class UsagePlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    included_media_bytes: int = Field(ge=0)
    included_db_bytes: int = Field(ge=0)
    max_members: int | None = Field(default=None, ge=1)


class UsagePlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    included_media_bytes: int | None = Field(default=None, ge=0)
    included_db_bytes: int | None = Field(default=None, ge=0)
    max_members: int | None = Field(default=None, ge=1)


class UsagePlanPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    included_media_bytes: int
    included_db_bytes: int
    max_members: int | None
    created_at: datetime
    updated_at: datetime


class ClinicPlanAssign(BaseModel):
    plan_id: UUID
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ClinicPlanAssignmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    plan_id: UUID
    plan_name: str
    starts_at: datetime
    ends_at: datetime | None
    created_at: datetime


class UsageRecomputeResult(BaseModel):
    clinics_processed: int
    snapshot_date: date


class S3ReconcileResult(BaseModel):
    clinic_id: UUID
    db_media_bytes: int
    s3_bytes: int
    s3_object_count: int
    delta_bytes: int


class ClinicInfraCostCreate(BaseModel):
    clinic_id: UUID
    period_start: date
    period_end: date
    cost_paise: int = Field(ge=0)
    source: str = Field(default="manual", max_length=64)
    notes: str | None = None


class ClinicInfraCostPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clinic_id: UUID
    period_start: date
    period_end: date
    cost_paise: int
    source: str
    notes: str | None
    created_at: datetime


class MediaQuotaCheck(BaseModel):
    allowed: bool
    current_media_bytes: int
    incoming_bytes: int
    limit_bytes: int | None
    status: UsageStatus
