"""Platform usage analytics integration tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.models.enums import SystemRole
from app.services.auth import store_password_for_local
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_platform_admin(db_session: AsyncSession, *, email: str) -> str:
    user_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, email, full_name, system_role, is_active)
            VALUES (:id, :email, 'Platform Admin', CAST(:role AS system_role), true);
            """
        ),
        {"id": str(user_id), "email": email, "role": SystemRole.PLATFORM_ADMIN.value},
    )
    await db_session.commit()
    store_password_for_local(email, user_id, "StrongPass123!")
    return email


async def _bootstrap_clinic(api_client: AsyncClient) -> tuple[str, str]:
    response = await api_client.post(
        "/auth/signup",
        json={
            "email": f"owner-{uuid4().hex[:8]}@example.com",
            "password": "StrongPass123!",
            "full_name": "Owner",
            "clinic_name": "Usage Clinic",
            "clinic_slug": f"usage-{uuid4().hex[:8]}",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = await api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    clinic_id = me.json()["memberships"][0]["clinic_id"]
    return token, clinic_id


@pytest.mark.asyncio
async def test_platform_usage_lists_clinics(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await _bootstrap_clinic(api_client)
    admin_email = await _create_platform_admin(
        db_session, email=f"platform-{uuid4().hex[:8]}@example.com"
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": admin_email, "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    admin_token = login.json()["access_token"]

    usage = await api_client.get(
        "/platform/usage/clinics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert usage.status_code == 200
    body = usage.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1
    assert "media_bytes" in body["items"][0]
    assert "patients_count" in body["items"][0]


@pytest.mark.asyncio
async def test_platform_usage_plans_and_recompute(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, clinic_id = await _bootstrap_clinic(api_client)
    admin_email = await _create_platform_admin(
        db_session, email=f"platform-{uuid4().hex[:8]}@example.com"
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": admin_email, "password": "StrongPass123!"},
    )
    admin_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    plans = await api_client.get("/platform/usage/plans", headers=headers)
    assert plans.status_code == 200
    starter = next(p for p in plans.json() if p["name"] == "Starter")

    assign = await api_client.post(
        f"/platform/usage/clinics/{clinic_id}/plan",
        headers=headers,
        json={"plan_id": starter["id"]},
    )
    assert assign.status_code == 201

    recompute = await api_client.post("/platform/usage/recompute", headers=headers)
    assert recompute.status_code == 200
    assert recompute.json()["clinics_processed"] >= 1

    history = await api_client.get(
        f"/platform/usage/clinics/{clinic_id}/history?days=7",
        headers=headers,
    )
    assert history.status_code == 200
    assert len(history.json()) >= 1
