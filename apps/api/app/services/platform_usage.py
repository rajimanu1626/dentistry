"""Platform usage analytics — per-clinic storage and activity rollups (no PHI)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import ObjectStorage
from app.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from app.models import (
    AuditLog,
    Clinic,
    ClinicInfraCost,
    ClinicMember,
    ClinicPlanAssignment,
    ClinicUsageSnapshot,
    ExternalShareLink,
    Patient,
    PatientMedia,
    Prescription,
    UsageEvent,
    UsagePlan,
    Visit,
)
from app.models.enums import enum_str
from app.schemas.platform_usage import (
    ClinicInfraCostCreate,
    ClinicInfraCostPublic,
    ClinicPlanAssign,
    ClinicPlanAssignmentPublic,
    ClinicUsageDetail,
    ClinicUsageMetrics,
    ClinicUsagePage,
    ClinicUsageSnapshotPublic,
    MediaKindBreakdown,
    MediaQuotaCheck,
    S3ReconcileResult,
    UsagePlanCreate,
    UsagePlanPublic,
    UsagePlanUpdate,
    UsageRecomputeResult,
    UsageStatus,
)

# Heuristic bytes per row for DB footprint estimates (encrypted PHI aware).
_PATIENT_ROW_BYTES = 4096
_VISIT_ROW_BYTES = 2048
_PRESCRIPTION_ROW_BYTES = 1024
_MEDIA_ROW_BYTES = 256
_AUDIT_ROW_BYTES = 512

_WARNING_PCT = 80.0


async def _disable_rls(session: AsyncSession) -> None:
    await session.execute(text("SET LOCAL row_security = off;"))


def _usage_status(
    *,
    media_bytes: int,
    db_bytes: int,
    included_media: int | None,
    included_db: int | None,
) -> UsageStatus:
    over = False
    warn = False
    if included_media is not None and included_media > 0:
        pct = (media_bytes / included_media) * 100
        if pct >= 100:
            over = True
        elif pct >= _WARNING_PCT:
            warn = True
    if included_db is not None and included_db > 0:
        pct = (db_bytes / included_db) * 100
        if pct >= 100:
            over = True
        elif pct >= _WARNING_PCT:
            warn = True
    if over:
        return UsageStatus.OVER_LIMIT
    if warn:
        return UsageStatus.WARNING
    return UsageStatus.OK


def _pct(used: int, limit: int | None) -> float | None:
    if limit is None or limit <= 0:
        return None
    return round((used / limit) * 100, 1)


async def _active_plan(session: AsyncSession, clinic_id: UUID) -> UsagePlan | None:
    now = datetime.now(UTC)
    row = await session.execute(
        select(UsagePlan, ClinicPlanAssignment)
        .join(ClinicPlanAssignment, ClinicPlanAssignment.plan_id == UsagePlan.id)
        .where(
            ClinicPlanAssignment.clinic_id == clinic_id,
            ClinicPlanAssignment.starts_at <= now,
            (ClinicPlanAssignment.ends_at.is_(None) | (ClinicPlanAssignment.ends_at > now)),
        )
        .order_by(ClinicPlanAssignment.starts_at.desc())
        .limit(1)
    )
    result = row.first()
    return result[0] if result else None


async def _compute_counts(session: AsyncSession, clinic_id: UUID) -> dict[str, int]:
    media = await session.execute(
        select(
            func.coalesce(func.sum(PatientMedia.bytes_size), 0),
            func.count(PatientMedia.id),
        ).where(PatientMedia.clinic_id == clinic_id)
    )
    media_bytes, media_count = media.one()

    patients = await session.scalar(
        select(func.count()).select_from(Patient).where(Patient.clinic_id == clinic_id)
    )
    visits = await session.scalar(
        select(func.count()).select_from(Visit).where(Visit.clinic_id == clinic_id)
    )
    prescriptions = await session.scalar(
        select(func.count()).select_from(Prescription).where(Prescription.clinic_id == clinic_id)
    )
    members = await session.scalar(
        select(func.count()).select_from(ClinicMember).where(ClinicMember.clinic_id == clinic_id)
    )
    audit_rows = await session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.clinic_id == clinic_id)
    )
    now = datetime.now(UTC)
    active_shares = await session.scalar(
        select(func.count())
        .select_from(ExternalShareLink)
        .where(
            ExternalShareLink.clinic_id == clinic_id,
            ExternalShareLink.revoked_at.is_(None),
            ExternalShareLink.expires_at > now,
        )
    )

    db_est = (
        int(patients or 0) * _PATIENT_ROW_BYTES
        + int(visits or 0) * _VISIT_ROW_BYTES
        + int(prescriptions or 0) * _PRESCRIPTION_ROW_BYTES
        + int(media_count or 0) * _MEDIA_ROW_BYTES
        + int(audit_rows or 0) * _AUDIT_ROW_BYTES
    )

    return {
        "media_bytes": int(media_bytes or 0),
        "media_count": int(media_count or 0),
        "patients_count": int(patients or 0),
        "visits_count": int(visits or 0),
        "prescriptions_count": int(prescriptions or 0),
        "members_count": int(members or 0),
        "audit_rows_count": int(audit_rows or 0),
        "active_external_shares_count": int(active_shares or 0),
        "db_bytes_estimated": db_est,
    }


async def _metrics_for_clinic(
    session: AsyncSession,
    clinic: Clinic,
    *,
    s3_bytes_reconciled: int | None = None,
) -> ClinicUsageMetrics:
    counts = await _compute_counts(session, clinic.id)
    plan = await _active_plan(session, clinic.id)
    status = _usage_status(
        media_bytes=counts["media_bytes"],
        db_bytes=counts["db_bytes_estimated"],
        included_media=plan.included_media_bytes if plan else None,
        included_db=plan.included_db_bytes if plan else None,
    )
    return ClinicUsageMetrics(
        clinic_id=clinic.id,
        clinic_name=clinic.name,
        clinic_slug=clinic.slug,
        s3_bytes_reconciled=s3_bytes_reconciled,
        plan_id=plan.id if plan else None,
        plan_name=plan.name if plan else None,
        included_media_bytes=plan.included_media_bytes if plan else None,
        included_db_bytes=plan.included_db_bytes if plan else None,
        media_usage_pct=_pct(counts["media_bytes"], plan.included_media_bytes if plan else None),
        db_usage_pct=_pct(counts["db_bytes_estimated"], plan.included_db_bytes if plan else None),
        status=status,
        **counts,
    )


async def list_clinic_usage(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
) -> ClinicUsagePage:
    await _disable_rls(session)
    total = await session.scalar(select(func.count()).select_from(Clinic)) or 0
    offset = (page - 1) * page_size
    rows = await session.execute(
        select(Clinic).order_by(Clinic.name.asc()).offset(offset).limit(page_size)
    )
    items = [await _metrics_for_clinic(session, c) for c in rows.scalars().all()]
    return ClinicUsagePage(items=items, total=int(total), page=page, page_size=page_size)


async def get_clinic_usage_detail(session: AsyncSession, *, clinic_id: UUID) -> ClinicUsageDetail:
    await _disable_rls(session)
    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise NotFoundError("Clinic not found.")
    base = await _metrics_for_clinic(session, clinic)

    kind_rows = await session.execute(
        select(PatientMedia.kind, func.count(), func.coalesce(func.sum(PatientMedia.bytes_size), 0))
        .where(PatientMedia.clinic_id == clinic_id)
        .group_by(PatientMedia.kind)
    )
    media_by_kind = [
        MediaKindBreakdown(kind=enum_str(k), count=int(c), bytes=int(b))
        for k, c, b in kind_rows.all()
    ]

    since = datetime.now(UTC) - timedelta(days=30)
    event_rows = await session.execute(
        select(UsageEvent.event_type, func.coalesce(func.sum(UsageEvent.quantity), 0))
        .where(UsageEvent.clinic_id == clinic_id, UsageEvent.created_at >= since)
        .group_by(UsageEvent.event_type)
    )
    usage_events_30d = {str(t): int(q) for t, q in event_rows.all()}

    return ClinicUsageDetail(
        **base.model_dump(),
        media_by_kind=media_by_kind,
        usage_events_30d=usage_events_30d,
    )


async def write_snapshot(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    snapshot_date: date | None = None,
    s3_bytes_reconciled: int | None = None,
) -> None:
    await _disable_rls(session)
    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise NotFoundError("Clinic not found.")
    day = snapshot_date or datetime.now(UTC).date()
    counts = await _compute_counts(session, clinic_id)
    now = datetime.now(UTC)
    stmt = insert(ClinicUsageSnapshot).values(
        id=uuid4(),
        clinic_id=clinic_id,
        snapshot_date=day,
        s3_bytes_reconciled=s3_bytes_reconciled,
        computed_at=now,
        **counts,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["clinic_id", "snapshot_date"],
        set_={
            **counts,
            "s3_bytes_reconciled": s3_bytes_reconciled,
            "computed_at": now,
        },
    )
    await session.execute(stmt)
    await session.commit()


async def rollup_all_clinics(
    session: AsyncSession,
    *,
    snapshot_date: date | None = None,
) -> UsageRecomputeResult:
    await _disable_rls(session)
    day = snapshot_date or datetime.now(UTC).date()
    clinic_ids = (await session.execute(select(Clinic.id))).scalars().all()
    for cid in clinic_ids:
        await write_snapshot(session, clinic_id=cid, snapshot_date=day)
    return UsageRecomputeResult(clinics_processed=len(clinic_ids), snapshot_date=day)


async def get_usage_history(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    days: int = 30,
) -> list[ClinicUsageSnapshotPublic]:
    await _disable_rls(session)
    since = datetime.now(UTC).date() - timedelta(days=max(1, min(days, 365)))
    rows = await session.execute(
        select(ClinicUsageSnapshot)
        .where(
            ClinicUsageSnapshot.clinic_id == clinic_id,
            ClinicUsageSnapshot.snapshot_date >= since,
        )
        .order_by(ClinicUsageSnapshot.snapshot_date.asc())
    )
    return [ClinicUsageSnapshotPublic.model_validate(r) for r in rows.scalars().all()]


async def export_usage_csv(
    session: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    await _disable_rls(session)
    q = select(ClinicUsageSnapshot, Clinic.name, Clinic.slug).join(
        Clinic, Clinic.id == ClinicUsageSnapshot.clinic_id
    )
    if date_from is not None:
        q = q.where(ClinicUsageSnapshot.snapshot_date >= date_from)
    if date_to is not None:
        q = q.where(ClinicUsageSnapshot.snapshot_date <= date_to)
    q = q.order_by(ClinicUsageSnapshot.snapshot_date.desc(), Clinic.name.asc())
    rows = await session.execute(q)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "snapshot_date",
            "clinic_id",
            "clinic_name",
            "clinic_slug",
            "media_bytes",
            "media_count",
            "patients_count",
            "visits_count",
            "prescriptions_count",
            "members_count",
            "audit_rows_count",
            "active_external_shares_count",
            "db_bytes_estimated",
            "s3_bytes_reconciled",
        ]
    )
    for snap, name, slug in rows.all():
        writer.writerow(
            [
                snap.snapshot_date.isoformat(),
                str(snap.clinic_id),
                name,
                slug,
                snap.media_bytes,
                snap.media_count,
                snap.patients_count,
                snap.visits_count,
                snap.prescriptions_count,
                snap.members_count,
                snap.audit_rows_count,
                snap.active_external_shares_count,
                snap.db_bytes_estimated,
                snap.s3_bytes_reconciled if snap.s3_bytes_reconciled is not None else "",
            ]
        )
    return buf.getvalue()


async def list_plans(session: AsyncSession) -> list[UsagePlanPublic]:
    await _disable_rls(session)
    rows = await session.execute(select(UsagePlan).order_by(UsagePlan.name.asc()))
    return [UsagePlanPublic.model_validate(p) for p in rows.scalars().all()]


async def create_plan(session: AsyncSession, *, body: UsagePlanCreate) -> UsagePlanPublic:
    await _disable_rls(session)
    plan = UsagePlan(
        name=body.name,
        included_media_bytes=body.included_media_bytes,
        included_db_bytes=body.included_db_bytes,
        max_members=body.max_members,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return UsagePlanPublic.model_validate(plan)


async def update_plan(
    session: AsyncSession,
    *,
    plan_id: UUID,
    body: UsagePlanUpdate,
) -> UsagePlanPublic:
    await _disable_rls(session)
    plan = await session.get(UsagePlan, plan_id)
    if plan is None:
        raise NotFoundError("Usage plan not found.")
    if body.name is not None:
        plan.name = body.name
    if body.included_media_bytes is not None:
        plan.included_media_bytes = body.included_media_bytes
    if body.included_db_bytes is not None:
        plan.included_db_bytes = body.included_db_bytes
    if body.max_members is not None:
        plan.max_members = body.max_members
    await session.commit()
    await session.refresh(plan)
    return UsagePlanPublic.model_validate(plan)


async def assign_plan_to_clinic(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    body: ClinicPlanAssign,
) -> ClinicPlanAssignmentPublic:
    await _disable_rls(session)
    clinic = await session.get(Clinic, clinic_id)
    if clinic is None:
        raise NotFoundError("Clinic not found.")
    plan = await session.get(UsagePlan, body.plan_id)
    if plan is None:
        raise NotFoundError("Usage plan not found.")
    starts = body.starts_at or datetime.now(UTC)
    assignment = ClinicPlanAssignment(
        clinic_id=clinic_id,
        plan_id=body.plan_id,
        starts_at=starts,
        ends_at=body.ends_at,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return ClinicPlanAssignmentPublic(
        id=assignment.id,
        clinic_id=assignment.clinic_id,
        plan_id=assignment.plan_id,
        plan_name=plan.name,
        starts_at=assignment.starts_at,
        ends_at=assignment.ends_at,
        created_at=assignment.created_at,
    )


async def check_media_quota(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    incoming_bytes: int,
) -> MediaQuotaCheck:
    await _disable_rls(session)
    counts = await _compute_counts(session, clinic_id)
    current = counts["media_bytes"]
    plan = await _active_plan(session, clinic_id)
    limit = plan.included_media_bytes if plan else None
    projected = current + incoming_bytes
    status = _usage_status(
        media_bytes=projected,
        db_bytes=counts["db_bytes_estimated"],
        included_media=limit,
        included_db=plan.included_db_bytes if plan else None,
    )
    allowed = status != UsageStatus.OVER_LIMIT or limit is None
    return MediaQuotaCheck(
        allowed=allowed,
        current_media_bytes=current,
        incoming_bytes=incoming_bytes,
        limit_bytes=limit,
        status=status,
    )


async def assert_media_upload_allowed(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    incoming_bytes: int,
) -> None:
    check = await check_media_quota(session, clinic_id=clinic_id, incoming_bytes=incoming_bytes)
    if not check.allowed:
        raise ForbiddenError(
            "This clinic has reached its included media storage limit. "
            "Contact platform support to upgrade the plan."
        )


async def record_usage_event(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    event_type: str,
    quantity: int = 1,
    metadata: dict[str, str] | None = None,
) -> None:
    """Append a billable usage event. Metadata must not contain PHI."""
    safe_meta = metadata or {}
    banned = {"phone", "email", "address", "full_name", "patient_code"}
    if banned.intersection(safe_meta.keys()):
        raise ValidationAppError("Usage event metadata must not contain PHI keys.")
    row = UsageEvent(
        clinic_id=clinic_id,
        event_type=event_type,
        quantity=quantity,
        metadata_=safe_meta,
    )
    session.add(row)
    await session.commit()


async def reconcile_s3_storage(
    session: AsyncSession,
    storage: ObjectStorage,
    *,
    clinic_id: UUID,
) -> S3ReconcileResult:
    await _disable_rls(session)
    prefix = f"{clinic_id}/"
    s3_bytes, s3_count = await storage.sum_prefix_bytes(prefix)
    counts = await _compute_counts(session, clinic_id)
    db_bytes = counts["media_bytes"]
    await write_snapshot(
        session,
        clinic_id=clinic_id,
        s3_bytes_reconciled=s3_bytes,
    )
    return S3ReconcileResult(
        clinic_id=clinic_id,
        db_media_bytes=db_bytes,
        s3_bytes=s3_bytes,
        s3_object_count=s3_count,
        delta_bytes=s3_bytes - db_bytes,
    )


async def import_infra_cost(
    session: AsyncSession,
    *,
    body: ClinicInfraCostCreate,
) -> ClinicInfraCostPublic:
    await _disable_rls(session)
    clinic = await session.get(Clinic, body.clinic_id)
    if clinic is None:
        raise NotFoundError("Clinic not found.")
    if body.period_end < body.period_start:
        raise ValidationAppError("period_end must be on or after period_start.")
    row = ClinicInfraCost(
        clinic_id=body.clinic_id,
        period_start=body.period_start,
        period_end=body.period_end,
        cost_paise=body.cost_paise,
        source=body.source,
        notes=body.notes,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ClinicInfraCostPublic.model_validate(row)


async def list_infra_costs(
    session: AsyncSession,
    *,
    clinic_id: UUID | None = None,
) -> list[ClinicInfraCostPublic]:
    await _disable_rls(session)
    q = select(ClinicInfraCost).order_by(ClinicInfraCost.period_start.desc())
    if clinic_id is not None:
        q = q.where(ClinicInfraCost.clinic_id == clinic_id)
    rows = await session.execute(q)
    return [ClinicInfraCostPublic.model_validate(r) for r in rows.scalars().all()]
