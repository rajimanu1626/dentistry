"""Clinic dashboard router — aggregate insights for the home page."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError
from app.db.session import get_session
from app.middleware.auth import Principal, require_clinical_access
from app.schemas.dashboard import ClinicDashboardStats
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _require_clinic(principal: Principal) -> UUID:
    if principal.current_clinic_id is None:
        raise ForbiddenError("X-Clinic-Id header is required.")
    return principal.current_clinic_id


@router.get("/stats", response_model=ClinicDashboardStats)
async def clinic_dashboard_stats(
    principal: Principal = Depends(require_clinical_access),
    session: AsyncSession = Depends(get_session),
) -> ClinicDashboardStats:
    clinic_id = _require_clinic(principal)
    return await service.get_clinic_dashboard_stats(session, clinic_id=clinic_id)
