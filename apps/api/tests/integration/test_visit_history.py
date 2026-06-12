from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _bootstrap_owner(api_client: AsyncClient, *, email: str = "owner-history@example.com") -> tuple[str, str]:
    response = await api_client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "StrongPass123!",
            "full_name": "Owner",
            "clinic_name": "History Clinic",
            "clinic_slug": "history-clinic",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = await api_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    clinic_id = me.json()["memberships"][0]["clinic_id"]
    return token, clinic_id


@pytest.mark.asyncio
async def test_patient_history_ordering_and_filters(api_client: AsyncClient) -> None:
    token, clinic_id = await _bootstrap_owner(api_client)
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": clinic_id}

    patient = await api_client.post(
        "/patients",
        headers=headers,
        json={"full_name": "History Patient", "notes": "timeline"},
    )
    patient_id = patient.json()["id"]

    visit = await api_client.post(
        "/visits",
        headers=headers,
        json={
            "patient_id": patient_id,
            "visit_date": "2026-01-02T10:00:00Z",
            "chief_complaint": "Pain",
            "diagnosis": "Caries",
        },
    )
    visit_id = visit.json()["id"]
    rx = await api_client.post(
        "/prescriptions",
        headers=headers,
        json={
            "visit_id": visit_id,
            "items": [{"medication": "Med A", "dose": "1", "frequency": "OD", "duration": "5d"}],
        },
    )
    assert rx.status_code == 201

    history = await api_client.get(f"/patients/{patient_id}/history", headers=headers)
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 2
    assert items[0]["event_time"] >= items[1]["event_time"]

    only_visits = await api_client.get(
        f"/patients/{patient_id}/history",
        headers=headers,
        params={"event_type": "visit"},
    )
    assert only_visits.status_code == 200
    assert all(item["event_type"] == "visit" for item in only_visits.json()["items"])


@pytest.mark.asyncio
async def test_visit_summary_and_patient_isolation(api_client: AsyncClient) -> None:
    owner_token, owner_clinic_id = await _bootstrap_owner(api_client, email="owner-summary@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Clinic-Id": owner_clinic_id}

    patient = await api_client.post(
        "/patients",
        headers=owner_headers,
        json={"full_name": "Summary Patient"},
    )
    patient_id = patient.json()["id"]
    visit = await api_client.post(
        "/visits",
        headers=owner_headers,
        json={"patient_id": patient_id, "visit_date": "2026-01-03T10:00:00Z", "notes": "summary note"},
    )
    visit_id = visit.json()["id"]

    summary = await api_client.get(f"/visits/{visit_id}/summary", headers=owner_headers)
    assert summary.status_code == 200
    assert summary.json()["visit"]["id"] == visit_id

    other_patient = await api_client.post(
        "/patients",
        headers=owner_headers,
        json={"full_name": "Other Patient"},
    )
    other_patient_id = other_patient.json()["id"]
    other_visit = await api_client.post(
        "/visits",
        headers=owner_headers,
        json={"patient_id": other_patient_id, "visit_date": "2026-01-04T10:00:00Z", "notes": "other"},
    )
    assert other_visit.status_code == 201

    history = await api_client.get(f"/patients/{patient_id}/history", headers=owner_headers)
    assert history.status_code == 200
    assert all(item["patient_id"] == patient_id for item in history.json()["items"])
