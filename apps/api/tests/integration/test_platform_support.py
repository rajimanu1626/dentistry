"""platform_support is read-only on /platform mutations."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.models.enums import SystemRole
from app.services.auth import store_password_for_local
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_platform_user(
    db_session: AsyncSession,
    *,
    email: str,
    role: SystemRole,
    password: str = "StrongPass123!",
) -> str:
    user_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, email, full_name, system_role, is_active)
            VALUES (:id, :email, :name, CAST(:role AS system_role), true);
            """
        ),
        {
            "id": str(user_id),
            "email": email,
            "name": "Platform User",
            "role": role.value,
        },
    )
    await db_session.commit()
    store_password_for_local(email, user_id, password)
    return email


async def _login(api_client: AsyncClient, email: str) -> str:
    res = await api_client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123!"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_platform_support_read_only(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    email = await _create_platform_user(
        db_session,
        email="support@example.com",
        role=SystemRole.PLATFORM_SUPPORT,
    )
    token = await _login(api_client, email)
    headers = {"Authorization": f"Bearer {token}"}

    list_res = await api_client.get("/platform/clinics", headers=headers)
    assert list_res.status_code == 200

    create_res = await api_client.post(
        "/platform/clinics",
        headers=headers,
        json={"name": "Blocked Clinic", "slug": "blocked-clinic"},
    )
    assert create_res.status_code == 403
