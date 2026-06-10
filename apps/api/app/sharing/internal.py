"""Internal patient sharing (doctor → doctor in the platform)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.models import (
    AuditAction,
    AuditLog,
    PatientShare,
    ShareRole,
    User,
)
from app.sharing.schemas import PatientShareCreate, PatientSharePublic

_MAX_DAYS = 365


async def create_share(
    session: AsyncSession,
    *,
    patient_id: UUID,
    source_clinic_id: UUID,
    body: PatientShareCreate,
    actor_user_id: UUID,
) -> PatientSharePublic:
    if body.expires_in_days > _MAX_DAYS:
        raise ValidationAppError(f"expires_in_days exceeds maximum ({_MAX_DAYS}).")

    async with session.begin():
        grantee_result = await session.execute(select(User).where(User.email == body.grantee_email))
        grantee = grantee_result.scalar_one_or_none()
        if grantee is None:
            raise NotFoundError("That email isn't registered on the platform.")
        if grantee.id == actor_user_id:
            raise ValidationAppError("You can't share a patient with yourself.")

        existing = await session.execute(
            select(PatientShare).where(
                PatientShare.patient_id == patient_id,
                PatientShare.grantee_user_id == grantee.id,
                PatientShare.revoked_at.is_(None),
                PatientShare.expires_at > datetime.now(UTC),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("An active share already exists for that grantee.")

        share = PatientShare(
            patient_id=patient_id,
            source_clinic_id=source_clinic_id,
            grantee_user_id=grantee.id,
            role=ShareRole(body.role),
            scope=body.scope,
            expires_at=datetime.now(UTC) + timedelta(days=body.expires_in_days),
            created_by=actor_user_id,
        )
        session.add(share)
        session.add(
            AuditLog(
                clinic_id=source_clinic_id,
                actor_user_id=actor_user_id,
                action=AuditAction.PATIENT_SHARE_CREATED,
                entity="patient_shares",
                entity_id=None,
                payload={
                    "patient_id": str(patient_id),
                    "grantee_email": body.grantee_email,
                    "role": body.role,
                    "expires_at": share.expires_at.isoformat(),
                },
            )
        )
        await session.flush()
        await session.refresh(share)
    return PatientSharePublic.model_validate(share)


async def list_shares_for_patient(
    session: AsyncSession, *, patient_id: UUID
) -> list[PatientSharePublic]:
    result = await session.execute(
        select(PatientShare)
        .where(PatientShare.patient_id == patient_id)
        .order_by(PatientShare.created_at.desc())
    )
    return [PatientSharePublic.model_validate(r) for r in result.scalars().all()]


async def revoke_share(
    session: AsyncSession,
    *,
    share_id: UUID,
    actor_user_id: UUID,
) -> None:
    async with session.begin():
        result = await session.execute(select(PatientShare).where(PatientShare.id == share_id))
        share = result.scalar_one_or_none()
        if share is None:
            raise NotFoundError("Share not found.")
        if share.revoked_at is not None:
            return
        share.revoked_at = datetime.now(UTC)
        session.add(
            AuditLog(
                clinic_id=share.source_clinic_id,
                actor_user_id=actor_user_id,
                action=AuditAction.PATIENT_SHARE_REVOKED,
                entity="patient_shares",
                entity_id=share.id,
                payload={"patient_id": str(share.patient_id)},
            )
        )
