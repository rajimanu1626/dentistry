"""Signup policy and gated registration (integration)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _bootstrap_owner(
    api_client: AsyncClient,
    *,
    email: str = "owner@example.com",
    clinic_name: str = "First Clinic",
    clinic_slug: str = "first-clinic",
) -> tuple[str, str]:
    response = await api_client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123!",
            "full_name": "Owner",
            "clinic_name": clinic_name,
            "clinic_slug": clinic_slug,
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = await api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    clinic_id = me.json()["memberships"][0]["clinic_id"]
    return token, clinic_id


@pytest.mark.asyncio
async def test_signup_blocked_without_invite_when_users_exist(api_client: AsyncClient) -> None:
    await _bootstrap_owner(api_client)

    second = await api_client.post(
        "/auth/signup",
        json={
            "email": "other@example.com",
            "password": "StrongPass123!",
            "full_name": "Other",
            "clinic_name": "Second Clinic",
            "clinic_slug": "second-clinic",
        },
    )
    assert second.status_code == 403
    assert second.json()["error"]["code"] == "forbidden"


@pytest.mark.asyncio
async def test_signup_with_invite_token(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(
        api_client,
        email="owner2@example.com",
        clinic_name="Invite Clinic",
        clinic_slug="invite-clinic",
    )

    invite = await api_client.post(
        "/auth/invites",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
        json={"email": "dentist@example.com", "role": "dentist"},
    )
    assert invite.status_code == 201
    invite_token = invite.json()["invite_token"]

    joined = await api_client.post(
        "/auth/signup",
        json={
            "email": "dentist@example.com",
            "password": "StrongPass123!",
            "full_name": "Invited Dentist",
            "invite_token": invite_token,
        },
    )
    assert joined.status_code == 201

    login = await api_client.post(
        "/auth/login",
        json={"email": "dentist@example.com", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    reused = await api_client.post(
        "/auth/signup",
        json={
            "email": "dentist-reuse@example.com",
            "password": "StrongPass123!",
            "full_name": "Invite Reuse",
            "invite_token": invite_token,
        },
    )
    assert reused.status_code == 410
    assert reused.json()["error"]["code"] == "gone"


@pytest.mark.asyncio
async def test_auth_config_reflects_policy(api_client: AsyncClient) -> None:
    response = await api_client.get("/auth/config")
    assert response.status_code == 200
    body = response.json()
    assert body["signup_mode"] == "invite"
    assert body["can_signup"] is True
    assert body["can_bootstrap_clinic"] is True
    assert body["requires_invite"] is False

    await api_client.post(
        "/auth/signup",
        json={
            "email": "cfg@example.com",
            "password": "StrongPass123!",
            "full_name": "Cfg",
            "clinic_name": "Cfg Clinic",
            "clinic_slug": "cfg-clinic",
        },
    )
    again = await api_client.get("/auth/config")
    assert again.json()["requires_invite"] is True
    assert again.json()["can_bootstrap_clinic"] is False


@pytest.mark.asyncio
async def test_invite_requires_clinic_header_and_succeeds_with_it(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(api_client)

    missing_header = await api_client.post(
        "/auth/invites",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "invite-no-header@example.com", "role": "dentist"},
    )
    assert missing_header.status_code == 403
    assert missing_header.json()["error"]["code"] == "forbidden"

    created = await api_client.post(
        "/auth/invites",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
        json={"email": "invite-with-header@example.com", "role": "dentist"},
    )
    assert created.status_code == 201
    assert isinstance(created.json()["invite_token"], str)
    assert len(created.json()["invite_token"]) >= 32


@pytest.mark.asyncio
async def test_patient_create_requires_clinic_header_and_succeeds(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(api_client)

    payload = {
        "full_name": "Rajesh",
        "date_of_birth": "1998-01-01",
        "sex": "M",
        "phone": "9976367152",
        "email": "rakeshking1998@gmail.com",
        "allergies": "none",
        "notes": "integration-test",
    }

    missing_header = await api_client.post(
        "/patients",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert missing_header.status_code == 403
    assert missing_header.json()["error"]["code"] == "forbidden"

    created = await api_client.post(
        "/patients",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
        json=payload,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["full_name"] == "Rajesh"
    assert body["clinic_id"] == clinic_id


@pytest.mark.asyncio
async def test_invite_list_and_revoke_flow(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(api_client, email="owner-list@example.com")

    created = await api_client.post(
        "/auth/invites",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
        json={"email": "revokable@example.com", "role": "assistant"},
    )
    assert created.status_code == 201
    invite_id = created.json()["invite_id"]
    invite_token = created.json()["invite_token"]

    listed = await api_client.get(
        "/auth/invites",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
    )
    assert listed.status_code == 200
    assert any(item["invite_id"] == invite_id for item in listed.json())

    revoked = await api_client.delete(
        f"/auth/invites/{invite_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Clinic-Id": clinic_id,
        },
    )
    assert revoked.status_code == 204

    blocked_signup = await api_client.post(
        "/auth/signup",
        json={
            "email": "revoked@example.com",
            "password": "StrongPass123!",
            "full_name": "Revoked Invite User",
            "invite_token": invite_token,
        },
    )
    assert blocked_signup.status_code == 410
    assert blocked_signup.json()["error"]["code"] == "gone"


@pytest.mark.asyncio
async def test_patient_update_and_delete_with_clinic_header(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(api_client, email="owner-patient-crud@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": clinic_id}

    created = await api_client.post(
        "/patients",
        headers=headers,
        json={
            "full_name": "CRUD Patient",
            "date_of_birth": "1992-02-02",
            "sex": "F",
            "phone": "9123456789",
            "email": "crud.patient@example.com",
            "allergies": "none",
            "notes": "before-update",
        },
    )
    assert created.status_code == 201
    patient_id = created.json()["id"]

    updated = await api_client.patch(
        f"/patients/{patient_id}",
        headers=headers,
        json={"notes": "after-update"},
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "after-update"

    deleted = await api_client.delete(f"/patients/{patient_id}", headers=headers)
    assert deleted.status_code == 204

    not_found = await api_client.get(f"/patients/{patient_id}", headers=headers)
    assert not_found.status_code == 404
