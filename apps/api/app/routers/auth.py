"""Auth router: signup, login, /me, invites."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider, get_identity_provider
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.middleware.auth import Principal, require_role, require_user
from app.models import Clinic, ClinicMember, User
from app.models.enums import ClinicRole
from app.schemas.auth import (
    AuthConfigPublic,
    ChangePasswordRequest,
    ClinicMembershipPublic,
    InviteCreated,
    InviteCreateRequest,
    InvitePublic,
    LoginRequest,
    MePublic,
    SignupRequest,
    TokenPair,
    UserPublic,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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
    user_row = await session.execute(select(User).where(User.id == principal.user_id))
    user = user_row.scalar_one()

    rows = await session.execute(
        select(ClinicMember.role, Clinic.id, Clinic.slug, Clinic.name)
        .join(Clinic, Clinic.id == ClinicMember.clinic_id)
        .where(ClinicMember.user_id == principal.user_id)
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
