"""Patients router. All endpoints require a clinic context (X-Clinic-Id)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError
from app.db.session import get_session
from app.middleware.auth import Principal, require_clinical_access
from app.models import PatientMedia
from app.schemas.patients import (
    PatientCreate,
    PatientPage,
    PatientPublic,
    PatientUpdate,
)
from app.services import patients as service
from app.services import visits as visits_service
from app.services.pdf import render_pdf

router = APIRouter(prefix="/patients", tags=["patients"])


def _require_clinic(principal: Principal) -> UUID:
    if principal.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    return principal.current_clinic_id


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


@router.get("", response_model=PatientPage)
async def list_patients(
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, max_length=160),
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PatientPage:
    clinic_id = _require_clinic(principal)
    return await service.list_patients(
        session,
        clinic_id=clinic_id,
        settings=settings,
        page=page,
        page_size=page_size,
        query=q,
    )


@router.post("", response_model=PatientPublic, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PatientPublic:
    clinic_id = _require_clinic(principal)
    return await service.create_patient(session, body=body, clinic_id=clinic_id, settings=settings)


@router.get("/{patient_id}", response_model=PatientPublic)
async def get_patient(
    patient_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PatientPublic:
    return await service.get_patient(session, patient_id=patient_id, settings=settings)


@router.patch("/{patient_id}", response_model=PatientPublic)
async def update_patient(
    patient_id: UUID,
    body: PatientUpdate,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PatientPublic:
    return await service.update_patient(
        session, patient_id=patient_id, body=body, settings=settings
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    await service.delete_patient(session, patient_id=patient_id)


@router.get("/{patient_id}/history/pdf", response_class=Response)
async def render_patient_history_pdf(
    patient_id: UUID,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> Response:
    _require_clinic(principal)
    patient = await service.get_patient(
        session,
        patient_id=patient_id,
        settings=get_settings(),
    )
    visits = await visits_service.list_visits_for_patient(session, patient_id=patient_id)
    media_rows = await session.execute(
        select(PatientMedia)
        .where(PatientMedia.patient_id == patient_id)
        .order_by(PatientMedia.created_at.asc())
    )
    media_by_visit: dict[str, list[dict[str, str]]] = {}
    for row in media_rows.scalars().all():
        if row.visit_id is None:
            continue
        key = str(row.visit_id)
        media_by_visit.setdefault(key, []).append(
            {
                "kind": row.kind.value,
                "filename": row.object_key.split("/")[-1] if row.object_key else "-",
                "captured_at_human": _humanize_datetime(
                    (row.taken_at or row.created_at).isoformat()
                ),
            }
        )
    visit_blocks: list[dict[str, object]] = []
    for visit in visits:
        prescriptions = await visits_service.list_prescriptions_for_visit(
            session, visit_id=visit.id
        )
        prescription_items = sorted(
            [p.model_dump(mode="json") for p in prescriptions],
            key=lambda rx: rx.get("created_at") or "",
        )
        visit_blocks.append(
            {
                "visit": visit.model_dump(mode="json"),
                "visit_date_human": _humanize_datetime(visit.visit_date.isoformat()),
                "prescriptions": prescription_items,
                "media_items": media_by_visit.get(str(visit.id), []),
            }
        )

    html_template = """
    <html><head><meta charset="utf-8"><title>Patient History</title></head>
    <body style="font-family: Arial, sans-serif; font-size: 12px;">
      <h1>Patient History Summary</h1>
      <p><strong>Patient:</strong> {{ patient.full_name }} ({{ patient.patient_code }})</p>
      {% for block in visits %}
        <hr />
        <h2>Visit {{ loop.index }} - {{ block.visit_date_human }}</h2>
        <p><strong>Chief complaint:</strong> {{ block.visit.chief_complaint or '-' }}</p>
        <p><strong>Diagnosis:</strong> {{ block.visit.diagnosis or '-' }}</p>
        <p><strong>Treatment plan:</strong> {{ block.visit.treatment_plan or '-' }}</p>
        <p><strong>Notes:</strong> {{ block.visit.notes or '-' }}</p>
        <p><strong>Prescriptions:</strong></p>
        {% if block.prescriptions|length == 0 %}
          <p>None</p>
        {% else %}
          {% for rx in block.prescriptions %}
            <ul>
              {% for item in rx['items'] %}
                <li>
                  {{ item.medication }} - {{ item.dose }} -
                  {{ item.frequency }} - {{ item.duration }}
                </li>
              {% endfor %}
            </ul>
            <p>{{ rx.notes or '' }}</p>
          {% endfor %}
        {% endif %}
        <p><strong>Media attached:</strong></p>
        {% if block.media_items|length == 0 %}
          <p>None</p>
        {% else %}
          <ul>
            {% for media in block.media_items %}
              <li>
                {{ media.kind }} - {{ media.filename }} - {{ media.captured_at_human }}
              </li>
            {% endfor %}
          </ul>
        {% endif %}
      {% endfor %}
    </body></html>
    """
    pdf_bytes = render_pdf(
        html_template,
        context={"patient": patient.model_dump(mode="json"), "visits": visit_blocks},
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="patient-history-{patient_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )
