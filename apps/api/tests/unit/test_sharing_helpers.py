"""Unit tests for sharing primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.security import constant_time_equals, hmac_sha256
from app.models import ExternalShareLink
from app.sharing.external import generate_readable_password, watermark_for


def test_generated_password_has_expected_shape() -> None:
    p = generate_readable_password()
    assert len(p) >= 10
    assert all(c.isalnum() or c in "-_" for c in p)
    # different each time
    assert generate_readable_password() != generate_readable_password()


def test_token_hmac_is_keyed() -> None:
    token = "abc123"
    a = hmac_sha256("secret-A", token)
    b = hmac_sha256("secret-B", token)
    assert not constant_time_equals(a, b)


def test_watermark_contains_share_id_and_label() -> None:
    fake_id = UUID("01234567-89ab-cdef-0123-456789abcdef")
    share = ExternalShareLink(
        id=fake_id,
        patient_id=uuid4(),
        clinic_id=uuid4(),
        token_hmac=b"x" * 32,
        password_hash="x",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        max_views=5,
        view_count=0,
        failed_attempts=0,
        recipient_label="Dr. Sharma @ Apollo",
    )
    wm = watermark_for(share)
    assert "Dr. Sharma @ Apollo" in wm
    assert str(fake_id) in wm
    assert "UTC" in wm
