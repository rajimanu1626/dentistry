"""Platform admin isolation and platform management APIs."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SystemRole
from app.services.auth import store_password_for_local


async def _bootstrap_owner_with_patient(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[str, str, str]:
    response = await api_client.post(
        "/auth/signup",
        json={
            "email": "owner-clinical@example.com",
            "password": "StrongPass123!",
            "full_name": "Clinical Owner",
            "clinic_name": "Clinical Clinic",
            "clinic_slug": "clinical-clinic",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = await api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    clinic_id = me.json()["memberships"][0]["clinic_id"]

    patient = await api_client.post(
        "/patients",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": clinic_id},
        json={"full_name": "PHI Patient", "phone": "9000001111"},
    )
    assert patient.status_code == 201
    patient_id = patient.json()["id"]
    return token, clinic_id, patient_id


async def _create_platform_admin(
    db_session: AsyncSession,
    *,
    email: str = "platform@example.com",
    password: str = "StrongPass123!",
) -> str:
    user_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, email, full_name, system_role, is_active)
            VALUES (:id, :email, :name, :role, true);
            """
        ),
        {
            "id": str(user_id),
            "email": email,
            "name": "Platform Admin",
            "role": SystemRole.PLATFORM_ADMIN.value,
        },
    )
    await db_session.commit()
    store_password_for_local(email, user_id, password)
    return email


@pytest.mark.asyncio
async def test_platform_admin_can_manage_clinics_but_not_patients(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_token, clinic_id, patient_id = await _bootstrap_owner_with_patient(
        api_client, db_session
    )
    platform_email = await _create_platform_admin(db_session)

    login = await api_client.post(
        "/auth/login",
        json={"email": platform_email, "password": "StrongPass123!"},
    )
    assert login.status_code == 200
    platform_token = login.json()["access_token"]

    me = await api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert me.status_code == 200
    assert me.json()["system_role"] == SystemRole.PLATFORM_ADMIN.value
    assert me.json()["memberships"] == []

    clinics = await api_client.get(
        "/platform/clinics",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert clinics.status_code == 200
    assert len(clinics.json()) >= 1

    created = await api_client.post(
        "/platform/clinics",
        headers={"Authorization": f"Bearer {platform_token}"},
        json={
            "name": "Platform Created Clinic",
            "slug": "platform-created-clinic",
            "address": "2 Ops Street",
        },
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "platform-created-clinic"

    denied = await api_client.get(
        f"/patients/{patient_id}",
        headers={
            "Authorization": f"Bearer {platform_token}",
            "X-Clinic-Id": clinic_id,
        },
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"

    owner_can = await api_client.get(
        f"/patients/{patient_id}",
        headers={
            "Authorization": f"Bearer {owner_token}",
            "X-Clinic-Id": clinic_id,
        },
    )
    assert owner_can.status_code == 200
    assert owner_can.json()["full_name"] == "PHI Patient"
