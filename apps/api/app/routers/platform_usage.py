"""Platform usage analytics routes (no PHI)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.storage import ObjectStorage, get_storage
from app.db.session import get_session
from app.middleware.auth import Principal, require_platform_admin, require_platform_operator
from app.schemas.platform_usage import (
    ClinicInfraCostCreate,
    ClinicInfraCostPublic,
    ClinicPlanAssign,
    ClinicPlanAssignmentPublic,
    ClinicUsageDetail,
    ClinicUsagePage,
    ClinicUsageSnapshotPublic,
    S3ReconcileResult,
    UsagePlanCreate,
    UsagePlanPublic,
    UsagePlanUpdate,
    UsageRecomputeResult,
)
from app.services import platform_usage as usage_service

router = APIRouter(prefix="/platform/usage", tags=["platform-usage"])


@router.get("/clinics", response_model=ClinicUsagePage)
async def list_clinic_usage(
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=200),
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> ClinicUsagePage:
    return await usage_service.list_clinic_usage(session, page=page, page_size=page_size)


@router.get("/clinics/{clinic_id}", response_model=ClinicUsageDetail)
async def get_clinic_usage(
    clinic_id: UUID,
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> ClinicUsageDetail:
    return await usage_service.get_clinic_usage_detail(session, clinic_id=clinic_id)


@router.get("/clinics/{clinic_id}/history", response_model=list[ClinicUsageSnapshotPublic])
async def get_clinic_usage_history(
    clinic_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[ClinicUsageSnapshotPublic]:
    return await usage_service.get_usage_history(session, clinic_id=clinic_id, days=days)


@router.post("/recompute", response_model=UsageRecomputeResult)
async def recompute_usage(
    snapshot_date: date | None = None,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> UsageRecomputeResult:
    return await usage_service.rollup_all_clinics(session, snapshot_date=snapshot_date)


@router.get("/export")
async def export_usage(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> Response:
    csv_body = await usage_service.export_usage_csv(session, date_from=date_from, date_to=date_to)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clinic-usage-export.csv"'},
    )


@router.get("/plans", response_model=list[UsagePlanPublic])
async def list_usage_plans(
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[UsagePlanPublic]:
    return await usage_service.list_plans(session)


@router.post("/plans", response_model=UsagePlanPublic, status_code=status.HTTP_201_CREATED)
async def create_usage_plan(
    body: UsagePlanCreate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> UsagePlanPublic:
    return await usage_service.create_plan(session, body=body)


@router.patch("/plans/{plan_id}", response_model=UsagePlanPublic)
async def update_usage_plan(
    plan_id: UUID,
    body: UsagePlanUpdate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> UsagePlanPublic:
    return await usage_service.update_plan(session, plan_id=plan_id, body=body)


@router.post(
    "/clinics/{clinic_id}/plan",
    response_model=ClinicPlanAssignmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def assign_clinic_plan(
    clinic_id: UUID,
    body: ClinicPlanAssign,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> ClinicPlanAssignmentPublic:
    return await usage_service.assign_plan_to_clinic(session, clinic_id=clinic_id, body=body)


@router.post("/clinics/{clinic_id}/reconcile-s3", response_model=S3ReconcileResult)
async def reconcile_clinic_s3(
    clinic_id: UUID,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
    storage: ObjectStorage = Depends(get_storage),
) -> S3ReconcileResult:
    return await usage_service.reconcile_s3_storage(session, storage, clinic_id=clinic_id)


@router.post(
    "/infra-costs",
    response_model=ClinicInfraCostPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_infra_cost(
    body: ClinicInfraCostCreate,
    _: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> ClinicInfraCostPublic:
    return await usage_service.import_infra_cost(session, body=body)


@router.get("/infra-costs", response_model=list[ClinicInfraCostPublic])
async def list_infra_costs(
    clinic_id: UUID | None = Query(default=None),
    _: Principal = Depends(require_platform_operator),
    session: AsyncSession = Depends(get_session),
) -> list[ClinicInfraCostPublic]:
    return await usage_service.list_infra_costs(session, clinic_id=clinic_id)
