"""Unit tests for core security helpers."""

from __future__ import annotations

from app.core.security import (
    constant_time_equals,
    hash_password,
    hmac_sha256,
    random_token,
    verify_password,
)


def test_password_roundtrip() -> None:
    h = hash_password("hunter22-LONG")
    assert verify_password("hunter22-LONG", h)
    assert not verify_password("WRONG", h)


def test_hash_is_unique_per_call() -> None:
    a = hash_password("same")
    b = hash_password("same")
    assert a != b


def test_random_token_has_min_length() -> None:
    t = random_token(16)
    assert len(t) >= 20  # base64url-encoded 16 bytes


def test_hmac_is_deterministic_and_keyed() -> None:
    a = hmac_sha256("k1", "msg")
    b = hmac_sha256("k1", "msg")
    c = hmac_sha256("k2", "msg")
    assert constant_time_equals(a, b)
    assert not constant_time_equals(a, c)
