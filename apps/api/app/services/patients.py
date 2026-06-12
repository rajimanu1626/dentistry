"""Patient service.

Encrypts PHI columns via Postgres ``pgp_sym_encrypt`` so the at-rest
representation is opaque to anyone who manages to bypass RLS (e.g. a leaked
``pg_dump``). The key lives in :class:`Settings.phi_encryption_key`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import NotFoundError
from app.schemas.patients import (
    PatientCreate,
    PatientListItem,
    PatientPage,
    PatientPublic,
    PatientUpdate,
)


async def create_patient(
    session: AsyncSession,
    *,
    body: PatientCreate,
    clinic_id: UUID,
    settings: Settings,
) -> PatientPublic:
    key = settings.phi_encryption_key.get_secret_value()
    try:
        result = await session.execute(
            text(
                """
                INSERT INTO patients (
                    clinic_id, full_name, date_of_birth, sex, email, notes,
                    phone_enc, address_enc, allergies_enc, medical_history_enc
                ) VALUES (
                    :clinic_id, :full_name, :dob, :sex, :email, :notes,
                    pgp_sym_encrypt(CAST(:phone AS text), CAST(:key AS text)),
                    pgp_sym_encrypt(CAST(:address AS text), CAST(:key AS text)),
                    pgp_sym_encrypt(CAST(:allergies AS text), CAST(:key AS text)),
                    pgp_sym_encrypt(CAST(:history AS text), CAST(:key AS text))
                )
                RETURNING id;
                """
            ),
            {
                "clinic_id": str(clinic_id),
                "full_name": body.full_name,
                "dob": body.date_of_birth,
                "sex": body.sex,
                "email": body.email,
                "notes": body.notes,
                "phone": body.phone,
                "address": body.address,
                "allergies": body.allergies,
                "history": body.medical_history,
                "key": key,
            },
        )
        new_id = result.scalar_one()
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return await get_patient(session, patient_id=new_id, settings=settings)


async def get_patient(
    session: AsyncSession,
    *,
    patient_id: UUID,
    settings: Settings,
) -> PatientPublic:
    key = settings.phi_encryption_key.get_secret_value()
    result = await session.execute(
        text(
            """
            SELECT
                id, clinic_id, patient_code, full_name, date_of_birth, sex,
                email, notes, created_at, updated_at,
                pgp_sym_decrypt(phone_enc, :key) AS phone,
                pgp_sym_decrypt(address_enc, :key) AS address,
                pgp_sym_decrypt(allergies_enc, :key) AS allergies,
                pgp_sym_decrypt(medical_history_enc, :key) AS medical_history
            FROM patients
            WHERE id = :id;
            """
        ),
        {"id": str(patient_id), "key": key},
    )
    row = result.mappings().first()
    if row is None:
        raise NotFoundError("Patient not found.")
    return PatientPublic.model_validate(dict(row))


async def list_patients(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    settings: Settings,
    page: int = 1,
    page_size: int = 20,
    query: str | None = None,
) -> PatientPage:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset_count = (page - 1) * page_size

    where_sql = "clinic_id = :clinic_id"
    params: dict[str, Any] = {"clinic_id": str(clinic_id)}
    if query:
        key = settings.phi_encryption_key.get_secret_value()
        where_sql += """
            AND (
                full_name ILIKE :q
                OR patient_code ILIKE :q
                OR CAST(id AS text) ILIKE :q
                OR CAST(pgp_sym_decrypt(phone_enc, CAST(:key AS text)) AS text) ILIKE :q
            )
        """
        params["q"] = f"%{query}%"
        params["key"] = key

    # where_sql is composed only of literal fragments + named bind params; safe.
    total_result = await session.execute(
        text(f"SELECT count(*) FROM patients WHERE {where_sql};"),  # noqa: S608
        params,
    )
    total = int(total_result.scalar_one())

    rows = await session.execute(
        text(
            f"""
            SELECT id, patient_code, full_name, date_of_birth, sex, created_at
            FROM patients
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset;
            """  # noqa: S608
        ),
        {**params, "limit": page_size, "offset": offset_count},
    )

    items = [PatientListItem.model_validate(dict(r)) for r in rows.mappings().all()]
    return PatientPage(items=items, total=total, page=page, page_size=page_size)


async def update_patient(
    session: AsyncSession,
    *,
    patient_id: UUID,
    body: PatientUpdate,
    settings: Settings,
) -> PatientPublic:
    key = settings.phi_encryption_key.get_secret_value()
    fields = body.model_dump(exclude_unset=True)

    sets: list[str] = []
    params: dict[str, Any] = {"id": str(patient_id), "key": key}

    plain_cols = {"full_name", "date_of_birth", "sex", "email", "notes"}
    enc_map = {
        "phone": "phone_enc",
        "address": "address_enc",
        "allergies": "allergies_enc",
        "medical_history": "medical_history_enc",
    }

    for k, v in fields.items():
        if k in plain_cols:
            sets.append(f"{k} = :p_{k}")
            params[f"p_{k}"] = v
        elif k in enc_map:
            col = enc_map[k]
            sets.append(f"{col} = pgp_sym_encrypt(CAST(:p_{k} AS text), CAST(:key AS text))")
            params[f"p_{k}"] = v

    if not sets:
        return await get_patient(session, patient_id=patient_id, settings=settings)

    sets.append("updated_at = now()")
    # `sets` is built from a fixed allow-list of column names; safe.
    update_sql = f"UPDATE patients SET {', '.join(sets)} WHERE id = :id RETURNING id;"  # noqa: S608
    try:
        result = await session.execute(text(update_sql), params)
        updated = result.scalar_one_or_none()
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    if updated is None:
        raise NotFoundError("Patient not found.")
    return await get_patient(session, patient_id=patient_id, settings=settings)


async def delete_patient(
    session: AsyncSession,
    *,
    patient_id: UUID,
) -> None:
    try:
        result = await session.execute(
            text("DELETE FROM patients WHERE id = :id RETURNING id;"),
            {"id": str(patient_id)},
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Patient not found.")
        await session.commit()
    except Exception:
        await session.rollback()
        raise


__all__ = [
    "create_patient",
    "delete_patient",
    "get_patient",
    "list_patients",
    "update_patient",
]
