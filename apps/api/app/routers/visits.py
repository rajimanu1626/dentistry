"""Routers for visits, prescriptions, and prescription templates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_session
from app.middleware.auth import Principal, require_clinical_access
from app.models import Clinic, Patient, Prescription
from app.schemas.visits import (
    PrescriptionCreate,
    PrescriptionPublic,
    PrescriptionTemplateCreate,
    PrescriptionTemplatePublic,
    VisitCreate,
    VisitHistoryPage,
    VisitPublic,
    VisitSummaryPublic,
    VisitUpdate,
)
from app.services import visits as service
from app.services.pdf import DEFAULT_PRESCRIPTION_TEMPLATE_HTML, render_pdf, utc_now_iso

visits_router = APIRouter(prefix="/visits", tags=["visits"])
rx_router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])
templates_router = APIRouter(prefix="/prescription-templates", tags=["prescriptions"])
history_router = APIRouter(prefix="/patients", tags=["visits"])


def _require_clinic(p: Principal) -> UUID:
    if p.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    return p.current_clinic_id


def _humanize_datetime(value: str | None) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    local_dt = dt.astimezone() if dt.tzinfo else dt.replace(tzinfo=UTC).astimezone()
    formatted = local_dt.strftime("%d %b %Y, %I:%M %p")
    return formatted.replace(" 0", " ")


# --------- visits ---------


@visits_router.post("", response_model=VisitPublic, status_code=status.HTTP_201_CREATED)
async def create_visit(
    body: VisitCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> VisitPublic:
    clinic_id = _require_clinic(principal)
    return await service.create_visit(session, body=body, clinic_id=clinic_id)


@visits_router.get("/{visit_id}", response_model=VisitPublic)
async def get_visit(
    visit_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> VisitPublic:
    return await service.get_visit(session, visit_id=visit_id)


@visits_router.patch("/{visit_id}", response_model=VisitPublic)
async def update_visit(
    visit_id: UUID,
    body: VisitUpdate,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> VisitPublic:
    return await service.update_visit(session, visit_id=visit_id, body=body)


@visits_router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(
    visit_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    await service.delete_visit(session, visit_id=visit_id)


@history_router.get("/{patient_id}/history", response_model=VisitHistoryPage)
async def get_patient_history(
    patient_id: UUID,
    event_type: list[str] | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> VisitHistoryPage:
    _require_clinic(principal)
    return await service.get_patient_history(
        session,
        patient_id=patient_id,
        event_types=set(event_type) if event_type else None,
        query=q,
        cursor=cursor,
        limit=limit,
    )


@visits_router.get("/{visit_id}/summary", response_model=VisitSummaryPublic)
async def get_visit_summary(
    visit_id: UUID,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> VisitSummaryPublic:
    _require_clinic(principal)
    return await service.get_visit_summary(session, visit_id=visit_id)


@visits_router.get("/{visit_id}/summary/pdf", response_class=Response)
async def render_visit_summary_pdf(
    visit_id: UUID,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> Response:
    _require_clinic(principal)
    summary = await service.get_visit_summary(session, visit_id=visit_id)
    visit_id_str = str(summary.visit.id)
    prescription_items = sorted(
        [p.model_dump(mode="json") for p in summary.prescriptions],
        key=lambda rx: rx.get("created_at") or "",
    )
    media_items = [
        {
            "kind": item.get("kind") or "other",
            "filename": (item.get("object_key") or "").split("/")[-1] or "-",
            "captured_at_raw": item.get("created_at") or "",
            "captured_at_human": _humanize_datetime(item.get("created_at")),
        }
        for item in summary.media
        if item.get("visit_id") in {None, visit_id_str}
    ]
    media_items.sort(key=lambda media: media["captured_at_raw"])

    html_template = """
    <html>
      <head><meta charset="utf-8"><title>Visit Summary</title></head>
      <body style="font-family: Arial, sans-serif; font-size: 13px;">
        <h1>Visit Summary</h1>
        <p><strong>Visit date:</strong> {{ visit_date_human }}</p>
        <p><strong>Chief complaint:</strong> {{ visit.chief_complaint or '-' }}</p>
        <p><strong>Diagnosis:</strong> {{ visit.diagnosis or '-' }}</p>
        <p><strong>Treatment plan:</strong> {{ visit.treatment_plan or '-' }}</p>
        <p><strong>Notes:</strong> {{ visit.notes or '-' }}</p>
        <h2>Prescriptions</h2>
        {% if prescriptions|length == 0 %}
          <p>No prescriptions.</p>
        {% else %}
          {% for rx in prescriptions %}
            <div style="margin-bottom: 12px;">
              <p><strong>Prescription {{ loop.index }}</strong></p>
              <ul>
                {% for item in rx['items'] %}
                  <li>
                    {{ item.medication }} - {{ item.dose }} -
                    {{ item.frequency }} - {{ item.duration }}
                  </li>
                {% endfor %}
              </ul>
              <p>{{ rx.notes or '' }}</p>
            </div>
          {% endfor %}
        {% endif %}
        <h2>Media attached</h2>
        {% if media_items|length == 0 %}
          <p>No media attached for this visit.</p>
        {% else %}
          <ul>
            {% for media in media_items %}
              <li>
                {{ media.kind }} - {{ media.filename }} - {{ media.captured_at_human }}
              </li>
            {% endfor %}
          </ul>
        {% endif %}
      </body>
    </html>
    """
    pdf_bytes = render_pdf(
        html_template,
        context={
            "visit": summary.visit.model_dump(mode="json"),
            "visit_date_human": _humanize_datetime(summary.visit.visit_date.isoformat()),
            "prescriptions": prescription_items,
            "media_items": media_items,
        },
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="visit-summary-{visit_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


# --------- prescriptions ---------


@rx_router.post("", response_model=PrescriptionPublic, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    body: PrescriptionCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> PrescriptionPublic:
    clinic_id = _require_clinic(principal)
    return await service.create_prescription(session, body=body, clinic_id=clinic_id)


@rx_router.get("/{rx_id}", response_model=PrescriptionPublic)
async def get_prescription(
    rx_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> PrescriptionPublic:
    return await service.get_prescription(session, rx_id=rx_id)


@rx_router.get("/{rx_id}/pdf", response_class=Response)
async def render_prescription_pdf(
    rx_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    rx = await service.get_prescription(session, rx_id=rx_id)
    template = await service.get_template_for_prescription(session, rx=rx)
    html_template = (
        template.html_template if template else DEFAULT_PRESCRIPTION_TEMPLATE_HTML.strip()
    )
    css = template.css if template else None

    visit = await service.get_visit(session, visit_id=rx.visit_id)
    patient_row = await session.execute(
        select(Patient.full_name, Patient.patient_code).where(Patient.id == visit.patient_id)
    )
    patient = patient_row.first()
    if patient is None:
        raise NotFoundError("Patient not found.")

    clinic_row = await session.execute(
        select(Clinic.name, Clinic.address).where(Clinic.id == rx.clinic_id)
    )
    clinic = clinic_row.first()

    pdf_bytes = render_pdf(
        html_template,
        context={
            "clinic": {
                "name": clinic.name if clinic else "Clinic",
                "address": clinic.address if clinic and clinic.address else "",
            },
            "patient": {
                "full_name": patient.full_name,
                "patient_code": patient.patient_code,
            },
            "dentist": {"full_name": "Doctor"},
            "items": rx.items,
            "notes": rx.notes,
            "visit_date": visit.visit_date.isoformat(),
            "generated_at": utc_now_iso(),
        },
        css=css,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="prescription-{rx_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


# --------- templates ---------


@templates_router.get("", response_model=list[PrescriptionTemplatePublic])
async def list_templates(
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> list[PrescriptionTemplatePublic]:
    clinic_id = _require_clinic(principal)
    return await service.list_templates(session, clinic_id=clinic_id)


@templates_router.post("", response_model=PrescriptionTemplatePublic, status_code=201)
async def create_template(
    body: PrescriptionTemplateCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> PrescriptionTemplatePublic:
    clinic_id = _require_clinic(principal)
    return await service.create_template(session, clinic_id=clinic_id, body=body)


_ = Prescription
