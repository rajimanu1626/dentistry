"""Auth dependencies.

`require_user` validates the Bearer JWT, loads the local ``users`` row, and
installs the RLS context (``app.current_user_id``) on the SQLAlchemy session
so subsequent queries are tenant-scoped.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider, get_identity_provider
from app.core.errors import ForbiddenError, UnauthorizedError
from app.db.session import get_session, set_rls_context
from app.models import ClinicMember, ClinicRole, User
from app.models.enums import SystemRole
from app.services.platform import is_platform_operator


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller."""

    user_id: UUID
    email: str
    current_clinic_id: UUID | None
    system_role: SystemRole | None


async def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedError("Missing Authorization header.")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Authorization header must be 'Bearer <token>'.")
    return parts[1].strip()


async def require_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_clinic_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    identity: IdentityProvider = Depends(get_identity_provider),
) -> Principal:
    """Resolve the calling user and install the RLS session context."""
    raw = await _bearer_token(authorization)
    token = await identity.verify(raw)

    result = await session.execute(select(User).where(User.id == token.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("Unknown or inactive user.")

    clinic_id: UUID | None = None
    if x_clinic_id:
        try:
            clinic_id = UUID(x_clinic_id)
        except ValueError as exc:
            raise UnauthorizedError("Invalid X-Clinic-Id header.") from exc
        membership = await session.execute(
            select(ClinicMember).where(
                ClinicMember.clinic_id == clinic_id,
                ClinicMember.user_id == user.id,
            )
        )
        if membership.scalar_one_or_none() is None:
            raise ForbiddenError("You are not a member of the requested clinic.")

    # Session may already be in an implicit transaction from the lookups above.
    # `SET LOCAL` requires a transaction, so reuse the active one instead of
    # opening a nested `session.begin()`.
    await set_rls_context(session, user_id=user.id, clinic_id=clinic_id)

    principal = Principal(
        user_id=user.id,
        email=user.email,
        current_clinic_id=clinic_id,
        system_role=user.system_role,
    )
    request.state.principal = principal
    return principal


async def require_clinical_access(
    principal: Principal = Depends(require_user),
) -> Principal:
    """Block platform operators from clinical endpoints (patients, visits, media)."""
    if is_platform_operator(principal.system_role):
        raise ForbiddenError("Platform operators cannot access clinical records.")
    return principal


async def require_platform_operator(
    principal: Principal = Depends(require_user),
) -> Principal:
    """Require platform_admin or platform_support (read-only console)."""
    if not is_platform_operator(principal.system_role):
        raise ForbiddenError("Platform operator access required.")
    return principal


async def require_platform_admin(
    principal: Principal = Depends(require_user),
) -> Principal:
    """Require an active platform admin account (mutations)."""
    if principal.system_role != SystemRole.PLATFORM_ADMIN:
        raise ForbiddenError("Platform admin access required.")
    return principal


def require_role(*allowed: ClinicRole):
    """Factory returning a dependency that enforces a clinic role."""

    async def _check(
        principal: Principal = Depends(require_user),
        session: AsyncSession = Depends(get_session),
    ) -> Principal:
        if principal.current_clinic_id is None:
            raise ForbiddenError("X-Clinic-Id header is required for this endpoint.")
        result = await session.execute(
            select(ClinicMember.role).where(
                ClinicMember.clinic_id == principal.current_clinic_id,
                ClinicMember.user_id == principal.user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None or row not in allowed:
            raise ForbiddenError("Insufficient role.")
        return principal

    return _check
