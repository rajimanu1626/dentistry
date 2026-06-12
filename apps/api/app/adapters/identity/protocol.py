"""Provider-agnostic identity protocol.

Everything outside ``app/adapters/identity`` imports only from this module so
swapping Supabase Auth -> Cognito -> Keycloak is purely a config change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IdentityToken:
    """Validated principal extracted from a JWT.

    Provider-specific claims may live in :attr:`extra`. The fields above are
    the ones our application code is allowed to depend on.
    """

    user_id: UUID
    email: str
    extra: dict[str, object]


class IdentityProvider(Protocol):
    """Validates JWTs and returns an :class:`IdentityToken`."""

    async def verify(self, raw_token: str) -> IdentityToken: ...

    async def issue(
        self,
        *,
        user_id: UUID,
        email: str,
        ttl_seconds: int | None = None,
        extra: dict[str, object] | None = None,
    ) -> str:
        """Mint a token. Used in tests and the ``local`` provider.

        Real-world Supabase / Cognito mint tokens on signup/login flows on
        the provider side, so this method is allowed to raise
        ``NotImplementedError`` for those adapters.
        """
        ...
