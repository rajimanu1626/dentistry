"""Dashboard DTOs — aggregate counts only, never PHI."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClinicDashboardStats(BaseModel):
    """Clinic-scoped operational snapshot for the home dashboard."""

    timezone: str = Field(description="Timezone used for day/week boundaries.")
    patients_total: int
    patients_added_today: int
    patients_added_this_week: int
    visits_today: int
    visits_this_week: int
    open_external_shares: int
