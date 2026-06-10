"""HTTP routers for internal + external sharing."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.identity import IdentityProvider, get_identity_provider
from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError
from app.db.session import get_session
from app.middleware.auth import Principal, require_clinical_access
from app.sharing import external as ext
from app.sharing import internal as ins
from app.sharing.schemas import (
    ExternalShareCreate,
    ExternalShareCreated,
    ExternalSharePublic,
    ExternalUnlockRequest,
    ExternalUnlockResponse,
    PatientShareCreate,
    PatientSharePublic,
)

# Rate-limiter used only on external-facing endpoints.
limiter = Limiter(key_func=get_remote_address)

internal_router = APIRouter(prefix="/patients/{patient_id}/shares", tags=["sharing"])
external_admin_router = APIRouter(prefix="/patients/{patient_id}/external-shares", tags=["sharing"])
external_public_router = APIRouter(prefix="/share", tags=["sharing-public"])


def _require_clinic(p: Principal) -> UUID:
    if p.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    return p.current_clinic_id


# --------------------------------------------------------------------------- #
# Internal (doctor-to-doctor)
# --------------------------------------------------------------------------- #


@internal_router.post("", response_model=PatientSharePublic, status_code=201)
async def create_internal_share(
    patient_id: UUID,
    body: PatientShareCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> PatientSharePublic:
    clinic_id = _require_clinic(principal)
    return await ins.create_share(
        session,
        patient_id=patient_id,
        source_clinic_id=clinic_id,
        body=body,
        actor_user_id=principal.user_id,
    )


@internal_router.get("", response_model=list[PatientSharePublic])
async def list_internal_shares(
    patient_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> list[PatientSharePublic]:
    return await ins.list_shares_for_patient(session, patient_id=patient_id)


@internal_router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_internal_share(
    patient_id: UUID,  # path arg for permission scoping
    share_id: UUID,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    _ = patient_id
    await ins.revoke_share(session, share_id=share_id, actor_user_id=principal.user_id)


# --------------------------------------------------------------------------- #
# External (admin endpoints — create / list / revoke)
# --------------------------------------------------------------------------- #


@external_admin_router.post(
    "", response_model=ExternalShareCreated, status_code=status.HTTP_201_CREATED
)
async def create_external_share(
    patient_id: UUID,
    body: ExternalShareCreate,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExternalShareCreated:
    clinic_id = _require_clinic(principal)
    return await ext.create_external_share(
        session,
        patient_id=patient_id,
        clinic_id=clinic_id,
        body=body,
        actor_user_id=principal.user_id,
        settings=settings,
    )


@external_admin_router.get("", response_model=list[ExternalSharePublic])
async def list_external_shares(
    patient_id: UUID,
    _: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> list[ExternalSharePublic]:
    return await ext.list_external_shares_for_patient(session, patient_id=patient_id)


@external_admin_router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_external_share(
    patient_id: UUID,
    share_id: UUID,
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> None:
    _ = patient_id
    await ext.revoke_external_share(session, share_id=share_id, actor_user_id=principal.user_id)


# --------------------------------------------------------------------------- #
# External (public unlock flow — no auth, rate-limited)
# --------------------------------------------------------------------------- #

_NO_INDEX_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@external_public_router.get("/{token}/summary")
@limiter.limit("20/minute")
async def share_landing(
    request: Request,
    token: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, str | None]:
    summary = await ext.landing_summary(session, raw_token=token, settings=settings)
    for k, v in _NO_INDEX_HEADERS.items():
        request.state.extra_headers = {**getattr(request.state, "extra_headers", {}), k: v}
    return summary


@external_public_router.post("/{token}/unlock", response_model=ExternalUnlockResponse)
@limiter.limit("10/minute")
async def unlock_share(
    request: Request,
    token: str,
    body: ExternalUnlockRequest,
    user_agent: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    identity: IdentityProvider = Depends(get_identity_provider),
) -> ExternalUnlockResponse:
    ip = request.client.host if request.client else None
    share, token_str, share_payload = await ext.unlock(
        session,
        raw_token=token,
        password=body.password,
        client_ip=ip,
        user_agent=user_agent,
        settings=settings,
        identity=identity,
    )
    return ExternalUnlockResponse(
        share_session_token=token_str,
        expires_in=15 * 60,
        patient_summary={
            "share_id": str(share.id),
            "recipient_label": share.recipient_label,
            **share_payload,
        },
    )
