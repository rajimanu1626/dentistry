"""Auth router: signup, login, /me, invites."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider, get_identity_provider
from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError
from app.db.session import get_session, set_rls_context
from app.middleware.auth import Principal, require_role, require_user
from app.models import Clinic, ClinicMember, User
from app.models.enums import ClinicRole
from app.schemas.auth import (
    AcceptInviteRequest,
    AuthConfigPublic,
    BootstrapClinicRequest,
    ChangePasswordRequest,
    ClinicMembershipPublic,
    InviteCreated,
    InviteCreateRequest,
    InvitePublic,
    LoginRequest,
    MePublic,
    SignupRequest,
    TokenPair,
    UpdateProfileRequest,
    UserPublic,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


async def _build_me(session: AsyncSession, user_id: UUID) -> MePublic:
    user_row = await session.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one()

    rows = await session.execute(
        select(ClinicMember.role, Clinic.id, Clinic.slug, Clinic.name)
        .join(Clinic, Clinic.id == ClinicMember.clinic_id)
        .where(ClinicMember.user_id == user_id)
    )
    memberships = [
        ClinicMembershipPublic(
            clinic_id=row.id,
            clinic_slug=row.slug,
            clinic_name=row.name,
            role=row.role,
        )
        for row in rows.all()
    ]
    return MePublic(
        user=UserPublic(id=user.id, email=user.email, full_name=user.full_name),
        memberships=memberships,
        system_role=user.system_role,
    )


@router.get("/config", response_model=AuthConfigPublic)
async def auth_config(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthConfigPublic:
    """Public signup policy for the web app."""
    policy = await auth_service.get_signup_policy(session, settings)
    return policy.to_public()


@router.post("/signup", response_model=TokenPair, status_code=201)
async def signup(
    body: SignupRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    identity: IdentityProvider = Depends(get_identity_provider),
) -> TokenPair:
    _, _, token = await auth_service.signup(
        session,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        clinic_name=body.clinic_name,
        clinic_slug=body.clinic_slug,
        invite_token=body.invite_token,
        settings=settings,
        identity=identity,
    )
    return TokenPair(
        access_token=token,
        refresh_token="",
        expires_in=settings.jwt_access_token_ttl_seconds,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    identity: IdentityProvider = Depends(get_identity_provider),
) -> TokenPair:
    _, token = await auth_service.login(
        session,
        email=body.email,
        password=body.password,
        settings=settings,
        identity=identity,
    )
    return TokenPair(
        access_token=token,
        refresh_token="",
        expires_in=settings.jwt_access_token_ttl_seconds,
    )


@router.get("/me", response_model=MePublic)
async def me(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MePublic:
    """Return the calling user and all of their clinic memberships."""
    return await _build_me(session, principal.user_id)


@router.patch("/me", response_model=MePublic)
async def update_me(
    body: UpdateProfileRequest,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MePublic:
    """Update the calling user's display profile."""
    await auth_service.update_profile(
        session,
        user_id=principal.user_id,
        full_name=body.full_name,
    )
    await set_rls_context(session, user_id=principal.user_id, clinic_id=None)
    return await _build_me(session, principal.user_id)


@router.post("/bootstrap-clinic", response_model=MePublic)
async def bootstrap_clinic(
    body: BootstrapClinicRequest,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MePublic:
    """Create the first clinic for an IdP-authenticated user (Neon/etc.)."""
    await auth_service.bootstrap_clinic_for_user(
        session,
        user_id=principal.user_id,
        clinic_name=body.clinic_name,
        clinic_slug=body.clinic_slug,
        full_name=body.full_name,
        settings=settings,
    )
    await set_rls_context(session, user_id=principal.user_id, clinic_id=None)
    return await _build_me(session, principal.user_id)


@router.post("/accept-invite", response_model=MePublic)
async def accept_invite(
    body: AcceptInviteRequest,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MePublic:
    """Accept a clinic invite for an IdP-authenticated user."""
    await auth_service.accept_invite_for_user(
        session,
        user_id=principal.user_id,
        email=principal.email,
        invite_token=body.invite_token,
        full_name=body.full_name,
        settings=settings,
    )
    await set_rls_context(session, user_id=principal.user_id, clinic_id=None)
    return await _build_me(session, principal.user_id)


@router.post("/invites", response_model=InviteCreated, status_code=201)
async def create_invite(
    body: InviteCreateRequest,
    principal: Principal = Depends(require_role(ClinicRole.OWNER)),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InviteCreated:
    """Create a clinic invite (owner only). Token is returned once."""
    assert principal.current_clinic_id is not None
    return await auth_service.create_clinic_invite(
        session,
        clinic_id=principal.current_clinic_id,
        body=body,
        invited_by=principal.user_id,
        settings=settings,
    )


@router.get("/invites", response_model=list[InvitePublic])
async def list_invites(
    principal: Principal = Depends(require_role(ClinicRole.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> list[InvitePublic]:
    """List clinic invites for the active clinic."""
    assert principal.current_clinic_id is not None
    return await auth_service.list_clinic_invites(session, clinic_id=principal.current_clinic_id)


@router.delete("/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: str,
    principal: Principal = Depends(require_role(ClinicRole.OWNER)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revoke a pending invite in the active clinic."""
    assert principal.current_clinic_id is not None
    await auth_service.revoke_clinic_invite(
        session,
        clinic_id=principal.current_clinic_id,
        invite_id=UUID(invite_id),
    )


@router.delete("/memberships/me", response_model=MePublic)
async def leave_clinic(
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> MePublic:
    """Leave the clinic identified by X-Clinic-Id."""
    if principal.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    await auth_service.leave_clinic(
        session,
        user_id=principal.user_id,
        clinic_id=principal.current_clinic_id,
    )
    await set_rls_context(session, user_id=principal.user_id, clinic_id=None)
    return await _build_me(session, principal.user_id)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    principal: Principal = Depends(require_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> None:
    """Change password for the current local-auth user."""
    await auth_service.change_password(
        session,
        user_id=principal.user_id,
        email=principal.email,
        current_password=body.current_password,
        new_password=body.new_password,
        settings=settings,
    )
