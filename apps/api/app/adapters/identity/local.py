"""Local HS256 JWT identity provider — used in dev + tests.

Production deployments use ``supabase`` or ``cognito`` which validate against
the IdP's JWKS endpoint. This file is the only place that talks to ``jose``.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import jwt

from app.adapters.identity.protocol import IdentityToken
from app.core.config import Settings
from app.core.errors import UnauthorizedError


class LocalIdentityProvider:
    """Signs + verifies HS256 JWTs with the configured signing key."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._key = settings.jwt_signing_key.get_secret_value()

    async def issue(
        self,
        *,
        user_id: UUID,
        email: str,
        ttl_seconds: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        now = int(time.time())
        ttl = ttl_seconds or self._settings.jwt_access_token_ttl_seconds
        payload: dict[str, Any] = {
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "sub": str(user_id),
            "email": email,
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, self._key, algorithm="HS256")

    async def verify(self, raw_token: str) -> IdentityToken:
        try:
            payload = jwt.decode(
                raw_token,
                self._key,
                algorithms=["HS256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError("Invalid authentication token.") from exc

        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise UnauthorizedError("Token is missing sub/email.")

        try:
            user_id = UUID(str(sub))
        except ValueError as exc:
            raise UnauthorizedError("Token sub is not a UUID.") from exc

        reserved = {"sub", "email", "iss", "aud", "iat", "exp", "nbf"}
        extra = {k: v for k, v in payload.items() if k not in reserved}
        return IdentityToken(user_id=user_id, email=str(email), extra=extra)
