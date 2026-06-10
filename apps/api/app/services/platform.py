"""Platform operator service (orgs/clinics/users — no PHI)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Clinic, ClinicGroup, User
from app.models.enums import SystemRole
from app.schemas.auth import InviteCreated, InviteCreateRequest
from app.schemas.platform import (
    PlatformClinicCreate,
    PlatformClinicPublic,
    PlatformGroupCreate,
    PlatformGroupPublic,
    PlatformUserPublic,
    PlatformUserUpdate,
)
from app.services import auth as auth_service
from app.services import visits as visits_service


async def _disable_rls(session: AsyncSession) -> None:
    await session.execute(text("SET LOCAL row_security = off;"))


async def list_groups(session: AsyncSession) -> list[PlatformGroupPublic]:
    await _disable_rls(session)
    rows = await session.execute(select(ClinicGroup).order_by(ClinicGroup.created_at.desc()))
    return [PlatformGroupPublic.model_validate(g) for g in rows.scalars().all()]


async def create_group(
    session: AsyncSession,
    *,
    body: PlatformGroupCreate,
) -> PlatformGroupPublic:
    try:
        await _disable_rls(session)
        owner = await session.execute(select(User.id).where(User.id == body.owner_user_id))
        if owner.scalar_one_or_none() is None:
            raise NotFoundError("Owner user not found.")
        group = ClinicGroup(name=body.name, owner_user_id=body.owner_user_id)
        session.add(group)
        await session.flush()
        await session.refresh(group)
        await session.commit()
    except NotFoundError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return PlatformGroupPublic.model_validate(group)


async def list_clinics(session: AsyncSession) -> list[PlatformClinicPublic]:
    await _disable_rls(session)
    rows = await session.execute(select(Clinic).order_by(Clinic.created_at.desc()))
    return [PlatformClinicPublic.model_validate(c) for c in rows.scalars().all()]


async def create_clinic(
    session: AsyncSession,
    *,
    body: PlatformClinicCreate,
) -> PlatformClinicPublic:
    try:
        await _disable_rls(session)
        existing = await session.execute(select(Clinic.id).where(Clinic.slug == body.slug))
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("That clinic slug is already taken.")
        if body.group_id is not None:
            group = await session.execute(
                select(ClinicGroup.id).where(ClinicGroup.id == body.group_id)
            )
            if group.scalar_one_or_none() is None:
                raise NotFoundError("Clinic group not found.")
        clinic = Clinic(
            slug=body.slug,
            name=body.name,
            group_id=body.group_id,
            address=body.address,
        )
        session.add(clinic)
        await session.flush()
        await visits_service.ensure_default_prescription_template(session, clinic_id=clinic.id)
        await session.refresh(clinic)
        await session.commit()
    except (ConflictError, NotFoundError):
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return PlatformClinicPublic.model_validate(clinic)


async def list_users(session: AsyncSession) -> list[PlatformUserPublic]:
    await _disable_rls(session)
    rows = await session.execute(select(User).order_by(User.created_at.desc()))
    return [
        PlatformUserPublic(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            system_role=u.system_role,
            created_at=u.created_at,
        )
        for u in rows.scalars().all()
    ]


async def update_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    body: PlatformUserUpdate,
) -> PlatformUserPublic:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return await get_user(session, user_id=user_id)
    try:
        await _disable_rls(session)
        row = await session.execute(select(User).where(User.id == user_id))
        user = row.scalar_one_or_none()
        if user is None:
            raise NotFoundError("User not found.")
        for key, value in fields.items():
            setattr(user, key, value)
        await session.commit()
    except NotFoundError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return PlatformUserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        system_role=user.system_role,
        created_at=user.created_at,
    )


async def get_user(session: AsyncSession, *, user_id: UUID) -> PlatformUserPublic:
    await _disable_rls(session)
    row = await session.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found.")
    return PlatformUserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        system_role=user.system_role,
        created_at=user.created_at,
    )


async def create_clinic_invite(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    body: InviteCreateRequest,
    invited_by: UUID,
    settings,
) -> InviteCreated:
    await _disable_rls(session)
    clinic = await session.execute(select(Clinic.id).where(Clinic.id == clinic_id))
    if clinic.scalar_one_or_none() is None:
        raise NotFoundError("Clinic not found.")
    return await auth_service.create_clinic_invite(
        session,
        clinic_id=clinic_id,
        body=body,
        invited_by=invited_by,
        settings=settings,
    )


def is_platform_operator(role: SystemRole | None) -> bool:
    return role in {SystemRole.PLATFORM_ADMIN, SystemRole.PLATFORM_SUPPORT}


__all__ = [
    "create_clinic",
    "create_clinic_invite",
    "create_group",
    "get_user",
    "is_platform_operator",
    "list_clinics",
    "list_groups",
    "list_users",
    "update_user",
]
