"""Clinic dashboard aggregates (counts only — no PHI)."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExternalShareLink, Patient, Visit
from app.schemas.dashboard import ClinicDashboardStats

DEFAULT_TZ = "Asia/Kolkata"


def _period_starts(*, tz_name: str = DEFAULT_TZ) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_today - timedelta(days=start_today.weekday())  # Monday
    return start_today, start_week, tz_name


async def get_clinic_dashboard_stats(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    tz_name: str = DEFAULT_TZ,
) -> ClinicDashboardStats:
    start_today, start_week, timezone = _period_starts(tz_name=tz_name)

    patients_total = int(
        (
            await session.execute(
                select(func.count()).select_from(Patient).where(Patient.clinic_id == clinic_id)
            )
        ).scalar_one()
    )
    patients_added_today = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Patient)
                .where(Patient.clinic_id == clinic_id, Patient.created_at >= start_today)
            )
        ).scalar_one()
    )
    patients_added_this_week = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Patient)
                .where(Patient.clinic_id == clinic_id, Patient.created_at >= start_week)
            )
        ).scalar_one()
    )
    visits_today = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Visit)
                .where(Visit.clinic_id == clinic_id, Visit.visit_date >= start_today)
            )
        ).scalar_one()
    )
    visits_this_week = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Visit)
                .where(Visit.clinic_id == clinic_id, Visit.visit_date >= start_week)
            )
        ).scalar_one()
    )
    open_shares = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ExternalShareLink)
                .where(
                    ExternalShareLink.clinic_id == clinic_id,
                    ExternalShareLink.revoked_at.is_(None),
                    ExternalShareLink.expires_at > func.now(),
                )
            )
        ).scalar_one()
    )

    return ClinicDashboardStats(
        timezone=timezone,
        patients_total=patients_total,
        patients_added_today=patients_added_today,
        patients_added_this_week=patients_added_this_week,
        visits_today=visits_today,
        visits_this_week=visits_this_week,
        open_external_shares=open_shares,
    )
