"""External (out-of-platform) patient sharing.

Issues a password-protected link, validates unlock attempts with lockout, and
returns a short-lived scoped session JWT that can only access ``/share/*``.

Security model
--------------
- Token in URL is 32-byte URL-safe random. The DB stores ``HMAC-SHA256(token,
  EXTERNAL_SHARE_HMAC_SECRET)`` so a leaked DB without the HMAC key is useless
  for replaying tokens.
- Password is **argon2id** hashed.
- 5 failed password attempts → ``revoked_at = now()``, share dead.
- Max-views and expiry are enforced server-side on every unlock.
- Audit logs every create / view / failed unlock / revoke.
"""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider
from app.core.config import Settings
from app.core.errors import GoneError, NotFoundError, UnauthorizedError
from app.core.security import (
    constant_time_equals,
    hash_password,
    hmac_sha256,
    random_token,
    verify_password,
)
from app.models import AuditAction, AuditLog, ExternalShareLink, Prescription, Visit
from app.sharing.schemas import (
    ExternalShareCreate,
    ExternalShareCreated,
    ExternalSharePublic,
)

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "-_"


def generate_readable_password(length: int = 14) -> str:
    """Return a high-entropy but copy-paste-friendly password."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


async def create_external_share(
    session: AsyncSession,
    *,
    patient_id: UUID,
    clinic_id: UUID,
    body: ExternalShareCreate,
    actor_user_id: UUID,
    settings: Settings,
) -> ExternalShareCreated:
    ttl = body.expires_in_seconds or settings.external_share_default_ttl_seconds
    if ttl > settings.external_share_max_ttl_seconds:
        ttl = settings.external_share_max_ttl_seconds

    raw_token = random_token(32)
    token_hmac = hmac_sha256(settings.external_share_hmac_secret.get_secret_value(), raw_token)
    password = body.password or generate_readable_password()

    share_id = uuid4()
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
    max_views = body.max_views or settings.external_share_max_views

    try:
        row = ExternalShareLink(
            id=share_id,
            patient_id=patient_id,
            clinic_id=clinic_id,
            token_hmac=token_hmac,
            password_hash=hash_password(password),
            scope=body.scope,
            expires_at=expires_at,
            max_views=max_views,
            view_count=0,
            failed_attempts=0,
            recipient_label=body.recipient_label,
            created_by=actor_user_id,
        )
        session.add(row)
        session.add(
            AuditLog(
                clinic_id=clinic_id,
                actor_user_id=actor_user_id,
                action=AuditAction.EXTERNAL_SHARE_CREATED,
                entity="external_share_links",
                entity_id=share_id,
                payload={
                    "patient_id": str(patient_id),
                    "expires_at": expires_at.isoformat(),
                    "max_views": max_views,
                    "recipient_label": body.recipient_label,
                },
                ip=None,
                user_agent=None,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    base = settings.app_base_url.rstrip("/")
    return ExternalShareCreated(
        id=share_id,
        url=f"{base}/share/{raw_token}",
        password=password,
        expires_at=expires_at,
        max_views=max_views,
    )


async def list_external_shares_for_patient(
    session: AsyncSession, *, patient_id: UUID
) -> list[ExternalSharePublic]:
    result = await session.execute(
        select(ExternalShareLink)
        .where(ExternalShareLink.patient_id == patient_id)
        .order_by(ExternalShareLink.created_at.desc())
    )
    return [ExternalSharePublic.model_validate(r) for r in result.scalars().all()]


async def revoke_external_share(
    session: AsyncSession,
    *,
    share_id: UUID,
    actor_user_id: UUID,
) -> None:
    async with session.begin():
        result = await session.execute(
            select(ExternalShareLink).where(ExternalShareLink.id == share_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError("Share not found.")
        if row.revoked_at is not None:
            return
        row.revoked_at = datetime.now(UTC)
        session.add(
            AuditLog(
                clinic_id=row.clinic_id,
                actor_user_id=actor_user_id,
                action=AuditAction.EXTERNAL_SHARE_REVOKED,
                entity="external_share_links",
                entity_id=row.id,
                payload={"patient_id": str(row.patient_id)},
            )
        )


# --------------------------------------------------------------------------- #
# Public unlock flow (no JWT yet — guards everything in the service layer)
# --------------------------------------------------------------------------- #


async def _resolve_by_token(
    session: AsyncSession, *, raw_token: str, settings: Settings
) -> ExternalShareLink:
    """Look up a share by raw token; raises if absent. **Constant-time** match."""
    if not raw_token or len(raw_token) > 256:
        raise NotFoundError("Invalid share token.")
    expected_hmac = hmac_sha256(settings.external_share_hmac_secret.get_secret_value(), raw_token)
    result = await session.execute(
        select(ExternalShareLink).where(ExternalShareLink.token_hmac == expected_hmac)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Share not found.")
    # Defense-in-depth: compare HMACs in constant time.
    if not constant_time_equals(bytes(row.token_hmac), expected_hmac):
        raise NotFoundError("Share not found.")
    return row


async def landing_summary(
    session: AsyncSession, *, raw_token: str, settings: Settings
) -> dict[str, Any]:
    """Return non-PHI metadata for the public landing page (initials + dob hint)."""
    row = await _resolve_by_token(session, raw_token=raw_token, settings=settings)
    if row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        raise GoneError("This share link is no longer valid.")
    if row.view_count >= row.max_views:
        raise GoneError("This share link has reached its view limit.")
    return {
        "share_id": str(row.id),
        "recipient_label": row.recipient_label,
        "expires_at": row.expires_at.isoformat(),
    }


async def unlock(
    session: AsyncSession,
    *,
    raw_token: str,
    password: str,
    client_ip: str | None,
    user_agent: str | None,
    settings: Settings,
    identity: IdentityProvider,
) -> tuple[ExternalShareLink, str, dict[str, Any]]:
    """Verify password and return (share, scoped_session_token)."""
    row = await _resolve_by_token(session, raw_token=raw_token, settings=settings)

    if row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        raise GoneError("This share link is no longer valid.")
    if row.view_count >= row.max_views:
        raise GoneError("This share link has reached its view limit.")
    if row.failed_attempts >= settings.external_share_max_password_attempts:
        raise GoneError("This share link is locked.")

    if not verify_password(password, row.password_hash):
        try:
            row.failed_attempts += 1
            should_revoke = row.failed_attempts >= settings.external_share_max_password_attempts
            if should_revoke:
                row.revoked_at = datetime.now(UTC)
            session.add(
                AuditLog(
                    clinic_id=row.clinic_id,
                    actor_user_id=None,
                    action=AuditAction.EXTERNAL_SHARE_FAILED_UNLOCK,
                    entity="external_share_links",
                    entity_id=row.id,
                    payload={
                        "attempt": row.failed_attempts,
                        "locked": bool(should_revoke),
                    },
                    ip=client_ip,
                    user_agent=user_agent,
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        raise UnauthorizedError("Wrong password.")

    try:
        row.view_count += 1
        row.last_accessed_at = datetime.now(UTC)
        row.last_accessed_ip = client_ip
        session.add(
            AuditLog(
                clinic_id=row.clinic_id,
                actor_user_id=None,
                action=AuditAction.EXTERNAL_SHARE_VIEWED,
                entity="external_share_links",
                entity_id=row.id,
                payload={"view_count": row.view_count},
                ip=client_ip,
                user_agent=user_agent,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    # Scoped 15-minute token, only valid against /share/* endpoints.
    session_token = await identity.issue(
        user_id=uuid4(),  # synthetic; the share_id claim is what matters
        email=row.recipient_label or "external-share",
        ttl_seconds=15 * 60,
        extra={"scope": "external_share", "share_id": str(row.id)},
    )
    mode = "visit"
    if isinstance(row.scope, dict):
        mode = str(row.scope.get("mode") or "visit")

    payload: dict[str, Any] = {"mode": mode}
    if mode == "history":
        visits_result = await session.execute(
            select(Visit)
            .where(Visit.patient_id == row.patient_id)
            .order_by(Visit.visit_date.desc())
        )
        visits = visits_result.scalars().all()
        history_items: list[dict[str, Any]] = []
        for visit in visits:
            prescriptions_result = await session.execute(
                select(Prescription)
                .where(Prescription.visit_id == visit.id)
                .order_by(Prescription.created_at.desc())
            )
            prescriptions = prescriptions_result.scalars().all()
            history_items.append(
                {
                    "visit_id": str(visit.id),
                    "visit_date": visit.visit_date.isoformat(),
                    "chief_complaint": visit.chief_complaint,
                    "diagnosis": visit.diagnosis,
                    "treatment_plan": visit.treatment_plan,
                    "notes": visit.notes,
                    "prescriptions": [
                        {
                            "items": p.items,
                            "notes": p.notes,
                            "created_at": p.created_at.isoformat(),
                        }
                        for p in prescriptions
                    ],
                }
            )
        payload["history_summary"] = {"patient_id": str(row.patient_id), "visits": history_items}
    else:
        visit_id_raw = row.scope.get("visit_id") if isinstance(row.scope, dict) else None
        visit = None
        if isinstance(visit_id_raw, str):
            try:
                visit_uuid = UUID(visit_id_raw)
            except ValueError:
                visit_uuid = None
            if visit_uuid is not None:
                visit_result = await session.execute(
                    select(Visit).where(Visit.id == visit_uuid, Visit.patient_id == row.patient_id)
                )
                visit = visit_result.scalar_one_or_none()
        if visit is None:
            visit_result = await session.execute(
                select(Visit)
                .where(Visit.patient_id == row.patient_id)
                .order_by(Visit.visit_date.desc())
            )
            visit = visit_result.scalar_one_or_none()

        if visit is not None:
            prescriptions_result = await session.execute(
                select(Prescription)
                .where(Prescription.visit_id == visit.id)
                .order_by(Prescription.created_at.desc())
            )
            prescriptions = prescriptions_result.scalars().all()
            payload["visit_summary"] = {
                "visit_id": str(visit.id),
                "visit_date": visit.visit_date.isoformat(),
                "chief_complaint": visit.chief_complaint,
                "diagnosis": visit.diagnosis,
                "treatment_plan": visit.treatment_plan,
                "notes": visit.notes,
                "prescriptions": [
                    {
                        "items": p.items,
                        "notes": p.notes,
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in prescriptions
                ],
            }

    return row, session_token, payload


def watermark_for(share: ExternalShareLink) -> str:
    """A human-visible string baked into the rendered HTML/PDF."""
    label = share.recipient_label or "External viewer"
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"{label} · share={share.id} · {ts}"
