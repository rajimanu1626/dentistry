"""Patient media: upload, list, signed-URL fetch, delete.

Image bytes never touch logs. EXIF is stripped before storage so we don't
accidentally persist GPS coordinates / device fingerprints.
"""

from __future__ import annotations

import io
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import ObjectStorage
from app.core.errors import NotFoundError, ValidationAppError
from app.models import MediaKind, PatientMedia

_ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024  # 8 MB


def strip_exif(data: bytes) -> tuple[bytes, str, tuple[int, int]]:
    """Re-encode the image without any EXIF metadata.

    Returns (clean_bytes, mime_type, (width, height)).
    Raises :class:`ValidationAppError` on unsupported / corrupt input.
    """
    if len(data) > _MAX_BYTES:
        raise ValidationAppError("Image too large (max 8 MB).")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationAppError("Unsupported or corrupt image.") from exc

    if img.format not in {"JPEG", "PNG", "WEBP"}:
        raise ValidationAppError(f"Unsupported image format: {img.format}")

    rgb = img.convert("RGB") if img.mode not in {"RGB", "RGBA"} else img
    buf = io.BytesIO()
    fmt = "JPEG" if img.format == "JPEG" else img.format
    rgb.save(buf, format=fmt, quality=88, optimize=True)
    out = buf.getvalue()
    mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[img.format]
    return out, mime, img.size


def build_object_key(*, clinic_id: UUID, patient_id: UUID, visit_id: UUID | None, kind: str) -> str:
    visit_part = str(visit_id) if visit_id else "no-visit"
    return f"{clinic_id}/{patient_id}/{visit_part}/{kind}-{uuid4().hex}.jpg"


async def upload_media(
    session: AsyncSession,
    storage: ObjectStorage,
    *,
    clinic_id: UUID,
    patient_id: UUID,
    visit_id: UUID | None,
    kind: MediaKind,
    raw_bytes: bytes,
    raw_mime: str,
    uploader_user_id: UUID,
) -> PatientMedia:
    if raw_mime not in _ALLOWED_MIMES:
        raise ValidationAppError(f"Unsupported mime type: {raw_mime}")

    clean, mime, (width, height) = strip_exif(raw_bytes)

    object_key = build_object_key(
        clinic_id=clinic_id,
        patient_id=patient_id,
        visit_id=visit_id,
        kind=kind.value,
    )
    uploaded = await storage.put_object(object_key=object_key, body=clean, mime_type=mime)

    async with session.begin():
        row = PatientMedia(
            clinic_id=clinic_id,
            patient_id=patient_id,
            visit_id=visit_id,
            kind=kind,
            object_key=uploaded.object_key,
            mime_type=mime,
            width_px=width,
            height_px=height,
            bytes_size=uploaded.bytes_size,
            uploaded_by=uploader_user_id,
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
    return row


async def list_media_for_patient(session: AsyncSession, *, patient_id: UUID) -> list[PatientMedia]:
    result = await session.execute(
        select(PatientMedia)
        .where(PatientMedia.patient_id == patient_id)
        .order_by(PatientMedia.created_at.desc())
    )
    return list(result.scalars().all())


async def signed_url_for(
    storage: ObjectStorage, media: PatientMedia, *, ttl: int | None = None
) -> str:
    return await storage.signed_get_url(media.object_key, ttl_seconds=ttl)


async def delete_media(
    session: AsyncSession,
    storage: ObjectStorage,
    *,
    media_id: UUID,
) -> None:
    async with session.begin():
        result = await session.execute(select(PatientMedia).where(PatientMedia.id == media_id))
        m = result.scalar_one_or_none()
        if m is None:
            raise NotFoundError("Media not found.")
        await storage.delete_object(m.object_key)
        await session.delete(m)
