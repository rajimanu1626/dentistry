"""Unit tests for the local HS256 identity provider."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.adapters.identity.local import LocalIdentityProvider
from app.core.config import Settings
from app.core.errors import UnauthorizedError


def _make_settings() -> Settings:
    return Settings(
        identity_provider="local",
        jwt_signing_key="0123456789abcdef0123456789abcdef",
        jwt_issuer="clinic-crm-test",
        jwt_audience="clinic-crm",
        jwt_access_token_ttl_seconds=60,
    )


@pytest.mark.asyncio
async def test_issue_and_verify_round_trip() -> None:
    settings = _make_settings()
    provider = LocalIdentityProvider(settings)
    uid = uuid4()
    token = await provider.issue(user_id=uid, email="foo@x.test")
    decoded = await provider.verify(token)
    assert decoded.user_id == uid
    assert decoded.email == "foo@x.test"


@pytest.mark.asyncio
async def test_verify_rejects_tampered_signature() -> None:
    settings = _make_settings()
    provider = LocalIdentityProvider(settings)
    token = await provider.issue(user_id=uuid4(), email="x@x.test")
    tampered = token + "x"
    with pytest.raises(UnauthorizedError):
        await provider.verify(tampered)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_audience() -> None:
    settings = _make_settings()
    provider = LocalIdentityProvider(settings)
    token = await provider.issue(user_id=uuid4(), email="x@x.test")

    other = LocalIdentityProvider(_make_settings_with(audience="other"))
    with pytest.raises(UnauthorizedError):
        await other.verify(token)


def _make_settings_with(*, audience: str) -> Settings:
    s = _make_settings()
    s.jwt_audience = audience
    return s
