"""Platform operator routes (orgs/clinics/users — no PHI)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.middleware.auth import (
    Principal,
    require_platform_admin,
    require_platform_operator,
)
from app.schemas.auth import InviteCreated, InviteCreateRequest
from app.schemas.platform import (
    PlatformClinicCreate,
    PlatformClinicInviteCreate,
    PlatformClinicPublic,
    PlatformGroupCreate,
    PlatformGroupPublic,
    PlatformUserPublic,
    PlatformUserUpdate,
)
from app.services import platform as platform_service

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/groups", response_model=list[PlatformGroupPublic])
async def list_groups(
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformGroupPublic]:
    return await platform_service.list_groups(session)


@router.post("/groups", response_model=PlatformGroupPublic, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: PlatformGroupCreate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> PlatformGroupPublic:
    return await platform_service.create_group(session, body=body)


@router.get("/clinics", response_model=list[PlatformClinicPublic])
async def list_clinics(
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformClinicPublic]:
    return await platform_service.list_clinics(session)


@router.post("/clinics", response_model=PlatformClinicPublic, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    body: PlatformClinicCreate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> PlatformClinicPublic:
    return await platform_service.create_clinic(session, body=body)


@router.post(
    "/clinics/{clinic_id}/invites",
    response_model=InviteCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_clinic_invite(
    clinic_id: UUID,
    body: PlatformClinicInviteCreate,
    principal: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> InviteCreated:
    return await platform_service.create_clinic_invite(
        session,
        clinic_id=clinic_id,
        body=InviteCreateRequest(
            email=body.email,
            role=body.role,
            expires_in_seconds=body.expires_in_seconds,
        ),
        invited_by=principal.user_id,
        settings=settings,
    )


@router.get("/users", response_model=list[PlatformUserPublic])
async def list_users(
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[PlatformUserPublic]:
    return await platform_service.list_users(session)


@router.patch("/users/{user_id}", response_model=PlatformUserPublic)
async def update_user(
    user_id: UUID,
    body: PlatformUserUpdate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> PlatformUserPublic:
    return await platform_service.update_user(session, user_id=user_id, body=body)
