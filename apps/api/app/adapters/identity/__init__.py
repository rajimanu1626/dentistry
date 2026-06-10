"""Identity provider adapter factory.

Selects the concrete adapter based on ``IDENTITY_PROVIDER`` env var.
Everything outside this package imports the :class:`IdentityProvider`
protocol so the rest of the code is provider-agnostic.
"""

from __future__ import annotations

from functools import lru_cache

from app.adapters.identity.jwks import JwksIdentityProvider
from app.adapters.identity.local import LocalIdentityProvider
from app.adapters.identity.protocol import IdentityProvider, IdentityToken
from app.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_identity_provider() -> IdentityProvider:
    settings: Settings = get_settings()
    if settings.identity_provider == "local":
        return LocalIdentityProvider(settings)
    return JwksIdentityProvider(settings)


__all__ = ["IdentityProvider", "IdentityToken", "get_identity_provider"]
