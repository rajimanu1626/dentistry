"""Visits + prescriptions service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.services.pdf import DEFAULT_PRESCRIPTION_TEMPLATE_HTML
from app.models import (
    ExternalShareLink,
    PatientMedia,
    PatientShare,
    Prescription,
    PrescriptionTemplate,
    Visit,
)
from app.schemas.visits import (
    PrescriptionCreate,
    PrescriptionPublic,
    PrescriptionTemplateCreate,
    PrescriptionTemplatePublic,
    VisitCreate,
    VisitHistoryItem,
    VisitHistoryPage,
    VisitPublic,
    VisitSummaryPublic,
    VisitUpdate,
)


async def create_visit(session: AsyncSession, *, body: VisitCreate, clinic_id: UUID) -> VisitPublic:
    try:
        v = Visit(
            clinic_id=clinic_id,
            patient_id=body.patient_id,
            dentist_id=body.dentist_id,
            visit_date=body.visit_date,
            chief_complaint=body.chief_complaint,
            diagnosis=body.diagnosis,
            treatment_plan=body.treatment_plan,
            notes=body.notes,
        )
        session.add(v)
        await session.flush()
        await session.refresh(v)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return VisitPublic.model_validate(v)


async def list_visits_for_patient(session: AsyncSession, *, patient_id: UUID) -> list[VisitPublic]:
    result = await session.execute(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc())
    )
    return [VisitPublic.model_validate(v) for v in result.scalars().all()]


async def get_visit(session: AsyncSession, *, visit_id: UUID) -> VisitPublic:
    result = await session.execute(select(Visit).where(Visit.id == visit_id))
    v = result.scalar_one_or_none()
    if v is None:
        raise NotFoundError("Visit not found.")
    return VisitPublic.model_validate(v)


async def update_visit(session: AsyncSession, *, visit_id: UUID, body: VisitUpdate) -> VisitPublic:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_visit(session, visit_id=visit_id)
    try:
        result = await session.execute(select(Visit).where(Visit.id == visit_id))
        v = result.scalar_one_or_none()
        if v is None:
            raise NotFoundError("Visit not found.")
        for k, val in fields.items():
            setattr(v, k, val)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return VisitPublic.model_validate(v)


async def delete_visit(session: AsyncSession, *, visit_id: UUID) -> None:
    try:
        result = await session.execute(select(Visit).where(Visit.id == visit_id))
        v = result.scalar_one_or_none()
        if v is None:
            raise NotFoundError("Visit not found.")
        await session.delete(v)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


# --------------------------------------------------------------------------- #
# Prescriptions
# --------------------------------------------------------------------------- #


async def create_prescription(
    session: AsyncSession, *, body: PrescriptionCreate, clinic_id: UUID
) -> PrescriptionPublic:
    try:
        rx = Prescription(
            clinic_id=clinic_id,
            visit_id=body.visit_id,
            template_id=body.template_id,
            items=[i.model_dump() for i in body.items],
            notes=body.notes,
        )
        session.add(rx)
        await session.flush()
        await session.refresh(rx)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return PrescriptionPublic.model_validate(rx)


async def list_prescriptions_for_visit(
    session: AsyncSession, *, visit_id: UUID
) -> list[PrescriptionPublic]:
    result = await session.execute(
        select(Prescription)
        .where(Prescription.visit_id == visit_id)
        .order_by(Prescription.created_at)
    )
    return [PrescriptionPublic.model_validate(p) for p in result.scalars().all()]


async def get_prescription(session: AsyncSession, *, rx_id: UUID) -> PrescriptionPublic:
    result = await session.execute(select(Prescription).where(Prescription.id == rx_id))
    p = result.scalar_one_or_none()
    if p is None:
        raise NotFoundError("Prescription not found.")
    return PrescriptionPublic.model_validate(p)


# --------------------------------------------------------------------------- #
# Prescription templates
# --------------------------------------------------------------------------- #


async def list_templates(
    session: AsyncSession, *, clinic_id: UUID
) -> list[PrescriptionTemplatePublic]:
    result = await session.execute(
        select(PrescriptionTemplate)
        .where(PrescriptionTemplate.clinic_id == clinic_id)
        .order_by(PrescriptionTemplate.is_default.desc(), PrescriptionTemplate.name)
    )
    return [PrescriptionTemplatePublic.model_validate(t) for t in result.scalars().all()]


async def create_template(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    body: PrescriptionTemplateCreate,
) -> PrescriptionTemplatePublic:
    try:
        if body.is_default:
            # Demote any other defaults.
            existing = await session.execute(
                select(PrescriptionTemplate).where(
                    PrescriptionTemplate.clinic_id == clinic_id,
                    PrescriptionTemplate.is_default.is_(True),
                )
            )
            for row in existing.scalars():
                row.is_default = False
        t = PrescriptionTemplate(
            clinic_id=clinic_id,
            name=body.name,
            html_template=body.html_template,
            css=body.css,
            is_default=body.is_default,
        )
        session.add(t)
        await session.flush()
        await session.refresh(t)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return PrescriptionTemplatePublic.model_validate(t)


async def ensure_default_prescription_template(
    session: AsyncSession, *, clinic_id: UUID
) -> None:
    """Provision the built-in default template for a new clinic."""
    existing = await session.execute(
        select(PrescriptionTemplate.id).where(
            PrescriptionTemplate.clinic_id == clinic_id,
            PrescriptionTemplate.is_default.is_(True),
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(
        PrescriptionTemplate(
            clinic_id=clinic_id,
            name="default",
            html_template=DEFAULT_PRESCRIPTION_TEMPLATE_HTML.strip(),
            is_default=True,
        )
    )


async def get_template_for_prescription(
    session: AsyncSession, *, rx: PrescriptionPublic
) -> PrescriptionTemplate | None:
    """Return the template to render `rx` with: explicit ``template_id`` or
    the clinic's default."""
    if rx.template_id:
        result = await session.execute(
            select(PrescriptionTemplate).where(PrescriptionTemplate.id == rx.template_id)
        )
        return result.scalar_one_or_none()
    result = await session.execute(
        select(PrescriptionTemplate).where(
            PrescriptionTemplate.clinic_id == rx.clinic_id,
            PrescriptionTemplate.is_default.is_(True),
        )
    )
    return result.scalar_one_or_none()


def _build_cursor(dt: datetime, row_id: UUID) -> str:
    return f"{dt.isoformat()}|{row_id}"


def _parse_cursor(cursor: str | None) -> tuple[datetime, UUID] | None:
    if not cursor:
        return None
    dt_raw, id_raw = cursor.split("|", 1)
    return datetime.fromisoformat(dt_raw), UUID(id_raw)


async def get_patient_history(
    session: AsyncSession,
    *,
    patient_id: UUID,
    event_types: set[str] | None = None,
    query: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> VisitHistoryPage:
    items: list[VisitHistoryItem] = []
    visit_ids: set[UUID] = set()

    if event_types is None or "visit" in event_types:
        visits = await session.execute(
            select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc())
        )
        for row in visits.scalars().all():
            items.append(
                VisitHistoryItem(
                    id=row.id,
                    event_type="visit",
                    event_time=row.visit_date,
                    visit_id=row.id,
                    patient_id=row.patient_id,
                    title="Visit logged",
                    summary=row.chief_complaint or row.diagnosis or row.notes,
                    metadata={"dentist_id": str(row.dentist_id) if row.dentist_id else None},
                )
            )
            visit_ids.add(row.id)

    if event_types is None or "prescription" in event_types:
        if not visit_ids:
            visit_rows = await session.execute(
                select(Visit.id).where(Visit.patient_id == patient_id)
            )
            visit_ids = {row.id for row in visit_rows}
        if visit_ids:
            rxs = await session.execute(
                select(Prescription).where(Prescription.visit_id.in_(visit_ids)).order_by(Prescription.created_at.desc())
            )
            for row in rxs.scalars().all():
                items.append(
                    VisitHistoryItem(
                        id=row.id,
                        event_type="prescription",
                        event_time=row.created_at,
                        visit_id=row.visit_id,
                        patient_id=patient_id,
                        title="Prescription issued",
                        summary=row.notes,
                        metadata={"items_count": len(row.items)},
                    )
                )

    if event_types is None or "media" in event_types:
        media_rows = await session.execute(
            select(PatientMedia)
            .where(PatientMedia.patient_id == patient_id)
            .order_by(PatientMedia.created_at.desc())
        )
        for row in media_rows.scalars().all():
            items.append(
                VisitHistoryItem(
                    id=row.id,
                    event_type="media",
                    event_time=row.taken_at or row.created_at,
                    visit_id=row.visit_id,
                    patient_id=row.patient_id,
                    title=f"Media uploaded ({row.kind.value})",
                    summary=row.object_key,
                    metadata={"mime_type": row.mime_type, "object_key": row.object_key},
                )
            )

    if event_types is None or "internal_share" in event_types:
        shares = await session.execute(
            select(PatientShare)
            .where(PatientShare.patient_id == patient_id)
            .order_by(PatientShare.created_at.desc())
        )
        for row in shares.scalars().all():
            items.append(
                VisitHistoryItem(
                    id=row.id,
                    event_type="internal_share",
                    event_time=row.created_at,
                    patient_id=row.patient_id,
                    title="Internal share created",
                    summary=f"role={row.role.value}",
                    metadata={
                        "grantee_user_id": str(row.grantee_user_id),
                        "expires_at": row.expires_at.isoformat(),
                        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
                    },
                )
            )

    if event_types is None or "external_share" in event_types:
        ex_shares = await session.execute(
            select(ExternalShareLink)
            .where(ExternalShareLink.patient_id == patient_id)
            .order_by(ExternalShareLink.created_at.desc())
        )
        for row in ex_shares.scalars().all():
            items.append(
                VisitHistoryItem(
                    id=row.id,
                    event_type="external_share",
                    event_time=row.created_at,
                    patient_id=row.patient_id,
                    title="External share created",
                    summary=row.recipient_label,
                    metadata={
                        "expires_at": row.expires_at.isoformat(),
                        "view_count": row.view_count,
                        "max_views": row.max_views,
                        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
                    },
                )
            )

    if query:
        q = query.strip().lower()
        items = [
            item
            for item in items
            if q in item.title.lower()
            or (item.summary and q in item.summary.lower())
            or q in item.event_type.lower()
        ]

    items.sort(key=lambda i: (i.event_time, i.id), reverse=True)

    cursor_tuple = _parse_cursor(cursor) if cursor else None
    if cursor_tuple:
        cursor_dt, cursor_id = cursor_tuple
        cursor_key = (cursor_dt, str(cursor_id))
        items = [
            item
            for item in items
            if (item.event_time, str(item.id)) < cursor_key
        ]

    page_items = items[:limit]
    next_cursor = None
    if len(items) > limit and page_items:
        last = page_items[-1]
        next_cursor = _build_cursor(last.event_time, last.id)

    return VisitHistoryPage(items=page_items, next_cursor=next_cursor)


async def get_visit_summary(
    session: AsyncSession,
    *,
    visit_id: UUID,
) -> VisitSummaryPublic:
    visit = await get_visit(session, visit_id=visit_id)
    prescriptions = await list_prescriptions_for_visit(session, visit_id=visit_id)
    media_rows = await session.execute(
        select(PatientMedia).where(
            or_(PatientMedia.visit_id == visit_id, PatientMedia.patient_id == visit.patient_id)
        )
    )
    media = [
        {
            "id": str(row.id),
            "kind": row.kind.value,
            "object_key": row.object_key,
            "mime_type": row.mime_type,
            "created_at": row.created_at.isoformat(),
            "visit_id": str(row.visit_id) if row.visit_id else None,
        }
        for row in media_rows.scalars().all()
    ]
    return VisitSummaryPublic(visit=visit, prescriptions=prescriptions, media=media)
