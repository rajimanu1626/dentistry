"""JWKS-based identity provider for Supabase Auth / AWS Cognito / Keycloak.

The provider is fully driven by the ``JWKS_URL`` env var so swapping providers
is a config change, not a code change. See ``CLAUDE.md`` -> Portability.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient

from app.adapters.identity.protocol import IdentityToken
from app.core.config import Settings
from app.core.errors import AppError, UnauthorizedError


class JwksIdentityProvider:
    """Validates RS256/ES256 JWTs against a remote JWKS document."""

    def __init__(self, settings: Settings) -> None:
        if not settings.jwks_url:
            raise AppError("JWKS_URL must be set for non-local IDENTITY_PROVIDER.")
        self._settings = settings
        self._jwk_client = PyJWKClient(settings.jwks_url, cache_keys=True)
        self._jwks_cached_at: float = 0.0
        self._http = httpx.AsyncClient(timeout=5.0)

    async def issue(self, **__: Any) -> str:  # pragma: no cover - never used in prod
        raise NotImplementedError("Token issuance is owned by the external IdP.")

    async def verify(self, raw_token: str) -> IdentityToken:
        if self._jwks_should_refresh():
            self._jwk_client.fetch_data()
            self._jwks_cached_at = time.time()
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(raw_token)
            payload = jwt.decode(
                raw_token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                options={"require": ["sub", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError("Invalid authentication token.") from exc

        sub = payload.get("sub")
        email = payload.get("email") or payload.get("preferred_username") or ""
        if not sub:
            raise UnauthorizedError("Token is missing sub.")
        try:
            user_id = UUID(str(sub))
        except ValueError as exc:
            raise UnauthorizedError("Token sub is not a UUID.") from exc

        extra = {
            k: v
            for k, v in payload.items()
            if k not in {"sub", "email", "iss", "aud", "iat", "exp", "nbf"}
        }
        return IdentityToken(user_id=user_id, email=str(email), extra=extra)

    def _jwks_should_refresh(self) -> bool:
        return (time.time() - self._jwks_cached_at) > self._settings.jwks_cache_ttl_seconds
