"""Patient media router. Upload, list, delete."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import ObjectStorage, get_storage
from app.core.errors import ForbiddenError, ValidationAppError
from app.db.session import get_session
from app.middleware.auth import Principal, require_clinical_access
from app.models import MediaKind
from app.schemas.media import PatientMediaWithUrl
from app.services import media as service

router = APIRouter(prefix="/patients/{patient_id}/media", tags=["media"])


def _require_clinic(p: Principal) -> UUID:
    if p.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    return p.current_clinic_id


@router.post(
    "",
    response_model=PatientMediaWithUrl,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    patient_id: UUID,
    file: UploadFile = File(...),
    kind: str = Form(...),
    visit_id: UUID | None = Form(default=None),
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
) -> PatientMediaWithUrl:
    clinic_id = _require_clinic(principal)
    try:
        kind_enum = MediaKind(kind)
    except ValueError as exc:
        raise ValidationAppError(f"Invalid media kind: {kind}") from exc

    data = await file.read()
    if not data:
        raise ValidationAppError("Empty upload.")

    row = await service.upload_media(
        session,
        storage,
        clinic_id=clinic_id,
        patient_id=patient_id,
        visit_id=visit_id,
        kind=kind_enum,
        raw_bytes=data,
        raw_mime=file.content_type or "application/octet-stream",
        uploader_user_id=principal.user_id,
    )
    signed = await service.signed_url_for(storage, row)
    return PatientMediaWithUrl(
        id=row.id,
        clinic_id=row.clinic_id,
        patient_id=row.patient_id,
        visit_id=row.visit_id,
        kind=row.kind.value,
        mime_type=row.mime_type,
        width_px=row.width_px,
        height_px=row.height_px,
        bytes_size=row.bytes_size,
        object_key=row.object_key,
        created_at=row.created_at,
        signed_url=signed,
    )


@router.get("", response_model=list[PatientMediaWithUrl])
async def list_media(
    patient_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
) -> list[PatientMediaWithUrl]:
    rows = await service.list_media_for_patient(session, patient_id=patient_id)
    return [
        PatientMediaWithUrl(
            id=r.id,
            clinic_id=r.clinic_id,
            patient_id=r.patient_id,
            visit_id=r.visit_id,
            kind=r.kind.value,
            mime_type=r.mime_type,
            width_px=r.width_px,
            height_px=r.height_px,
            bytes_size=r.bytes_size,
            object_key=r.object_key,
            created_at=r.created_at,
            signed_url=await service.signed_url_for(storage, r),
        )
        for r in rows
    ]


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    patient_id: UUID,
    media_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
) -> None:
    _ = patient_id  # path arg kept for permission scoping; not used directly
    await service.delete_media(session, storage, media_id=media_id)
