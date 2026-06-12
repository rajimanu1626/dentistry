"""Verify image upload sanitisation: EXIF strip + size validation."""

from __future__ import annotations

import io

import pytest
from app.core.errors import ValidationAppError
from app.services.media import build_object_key, strip_exif
from PIL import Image
from PIL.ExifTags import Base as ExifTag


def _gps_jpeg() -> bytes:
    img = Image.new("RGB", (32, 24), color=(255, 0, 0))
    exif = img.getexif()
    exif[ExifTag.Make] = "TestCam"
    exif[ExifTag.Software] = "test-suite"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def test_strip_exif_removes_metadata() -> None:
    src = _gps_jpeg()
    out, mime, size = strip_exif(src)

    parsed = Image.open(io.BytesIO(out))
    parsed.load()
    new_exif = parsed.getexif()
    assert ExifTag.Make not in new_exif
    assert ExifTag.Software not in new_exif
    assert mime == "image/jpeg"
    assert size == (32, 24)


def test_strip_exif_rejects_garbage() -> None:
    with pytest.raises(ValidationAppError):
        strip_exif(b"not an image at all")


def test_strip_exif_rejects_oversized() -> None:
    huge = b"\xff" * (9 * 1024 * 1024)
    with pytest.raises(ValidationAppError):
        strip_exif(huge)


def test_build_object_key_namespaces_correctly() -> None:
    from uuid import UUID

    clinic = UUID("11111111-1111-1111-1111-111111111111")
    patient = UUID("22222222-2222-2222-2222-222222222222")
    visit = UUID("33333333-3333-3333-3333-333333333333")
    key = build_object_key(clinic_id=clinic, patient_id=patient, visit_id=visit, kind="before")
    assert key.startswith(f"{clinic}/{patient}/{visit}/before-")
    assert key.endswith(".jpg")


def test_build_object_key_when_visit_is_none() -> None:
    from uuid import UUID

    clinic = UUID("11111111-1111-1111-1111-111111111111")
    patient = UUID("22222222-2222-2222-2222-222222222222")
    key = build_object_key(clinic_id=clinic, patient_id=patient, visit_id=None, kind="after")
    assert key.startswith(f"{clinic}/{patient}/no-visit/after-")
