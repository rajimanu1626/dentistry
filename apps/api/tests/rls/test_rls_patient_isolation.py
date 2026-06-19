"""Verify the RLS policies isolate clinics.

We create two clinics with one user/patient each and assert that, while
running under user A's session context, **no** query (raw SQL or ORM) can
observe clinic B's rows. We also verify the sharing escape hatch works.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.db.session import clear_rls_context, set_rls_context
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.asyncio, pytest.mark.rls, pytest.mark.integration]


async def _seed_two_clinics(db_session: AsyncSession) -> dict[str, str]:
    """Bootstrap: 2 clinics, 2 users, 2 patients. Returns id map."""
    user_a, user_b = uuid4(), uuid4()
    clinic_a, clinic_b = uuid4(), uuid4()

    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        await db_session.execute(
            text("INSERT INTO users (id, email) VALUES (:ua, :ea), (:ub, :eb)"),
            {"ua": str(user_a), "ea": "a@x.test", "ub": str(user_b), "eb": "b@x.test"},
        )
        await db_session.execute(
            text("INSERT INTO clinics (id, slug, name) VALUES (:ca, 'a', 'A'), (:cb, 'b', 'B')"),
            {"ca": str(clinic_a), "cb": str(clinic_b)},
        )
        await db_session.execute(
            text(
                "INSERT INTO clinic_members (clinic_id, user_id, role) VALUES "
                "(:ca, :ua, 'owner'), (:cb, :ub, 'owner')"
            ),
            {
                "ca": str(clinic_a),
                "ua": str(user_a),
                "cb": str(clinic_b),
                "ub": str(user_b),
            },
        )
        result = await db_session.execute(
            text(
                "INSERT INTO patients (clinic_id, full_name) VALUES "
                "(:ca, 'Alice A'), (:cb, 'Bob B') RETURNING id, clinic_id;"
            ),
            {"ca": str(clinic_a), "cb": str(clinic_b)},
        )
        rows = result.all()
        patient_ids = {str(r.clinic_id): str(r.id) for r in rows}

    return {
        "user_a": str(user_a),
        "user_b": str(user_b),
        "clinic_a": str(clinic_a),
        "clinic_b": str(clinic_b),
        "patient_a": patient_ids[str(clinic_a)],
        "patient_b": patient_ids[str(clinic_b)],
    }


async def test_user_a_cannot_see_clinic_b_patients(db_session: AsyncSession) -> None:
    ids = await _seed_two_clinics(db_session)

    async with db_session.begin():
        from uuid import UUID

        await set_rls_context(db_session, user_id=UUID(ids["user_a"]))
        result = await db_session.execute(
            text("SELECT id, clinic_id, full_name FROM patients ORDER BY full_name;")
        )
        rows = result.all()

    assert len(rows) == 1, f"expected only clinic A's patient visible, got {rows}"
    assert str(rows[0].clinic_id) == ids["clinic_a"]
    assert rows[0].full_name == "Alice A"


async def test_user_b_cannot_see_clinic_a_patients(db_session: AsyncSession) -> None:
    ids = await _seed_two_clinics(db_session)

    async with db_session.begin():
        from uuid import UUID

        await set_rls_context(db_session, user_id=UUID(ids["user_b"]))
        result = await db_session.execute(text("SELECT id, full_name FROM patients;"))
        rows = result.all()

    assert len(rows) == 1
    assert rows[0].full_name == "Bob B"


async def test_unauthenticated_session_sees_nothing(db_session: AsyncSession) -> None:
    await _seed_two_clinics(db_session)

    async with db_session.begin():
        await clear_rls_context(db_session)
        result = await db_session.execute(text("SELECT count(*) AS n FROM patients;"))
        n = result.scalar_one()

    assert n == 0


async def test_patient_share_grants_cross_clinic_visibility(db_session: AsyncSession) -> None:
    ids = await _seed_two_clinics(db_session)

    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        await db_session.execute(
            text(
                "INSERT INTO patient_shares "
                "(patient_id, source_clinic_id, grantee_user_id, role, expires_at) "
                "VALUES (:pid, :src, :grantee, 'viewer', :exp);"
            ),
            {
                "pid": ids["patient_a"],
                "src": ids["clinic_a"],
                "grantee": ids["user_b"],
                "exp": datetime.now(UTC) + timedelta(days=7),
            },
        )

    async with db_session.begin():
        from uuid import UUID

        await set_rls_context(db_session, user_id=UUID(ids["user_b"]))
        result = await db_session.execute(
            text("SELECT full_name FROM patients ORDER BY full_name;")
        )
        names = [r.full_name for r in result.all()]

    assert names == ["Alice A", "Bob B"], "user B should see own + shared patient"


async def test_expired_patient_share_loses_visibility(db_session: AsyncSession) -> None:
    ids = await _seed_two_clinics(db_session)

    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        await db_session.execute(
            text(
                "INSERT INTO patient_shares "
                "(patient_id, source_clinic_id, grantee_user_id, role, expires_at) "
                "VALUES (:pid, :src, :grantee, 'viewer', :exp);"
            ),
            {
                "pid": ids["patient_a"],
                "src": ids["clinic_a"],
                "grantee": ids["user_b"],
                "exp": datetime.now(UTC) - timedelta(minutes=1),
            },
        )

    async with db_session.begin():
        from uuid import UUID

        await set_rls_context(db_session, user_id=UUID(ids["user_b"]))
        result = await db_session.execute(
            text("SELECT full_name FROM patients WHERE clinic_id = :ca;"),
            {"ca": ids["clinic_a"]},
        )
        rows = result.all()

    assert rows == [], "expired share must not grant visibility"


async def test_revoked_patient_share_loses_visibility(db_session: AsyncSession) -> None:
    ids = await _seed_two_clinics(db_session)

    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        await db_session.execute(
            text(
                "INSERT INTO patient_shares "
                "(patient_id, source_clinic_id, grantee_user_id, role, expires_at, revoked_at) "
                "VALUES (:pid, :src, :grantee, 'viewer', :exp, now());"
            ),
            {
                "pid": ids["patient_a"],
                "src": ids["clinic_a"],
                "grantee": ids["user_b"],
                "exp": datetime.now(UTC) + timedelta(days=7),
            },
        )

    async with db_session.begin():
        from uuid import UUID

        await set_rls_context(db_session, user_id=UUID(ids["user_b"]))
        result = await db_session.execute(
            text("SELECT full_name FROM patients WHERE clinic_id = :ca;"),
            {"ca": ids["clinic_a"]},
        )
        rows = result.all()

    assert rows == [], "revoked share must not grant visibility"


async def test_patient_code_auto_generated(db_session: AsyncSession) -> None:
    """The BEFORE INSERT trigger assigns DC-YYYY-NNNNN per clinic."""
    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        clinic_id = uuid4()
        await db_session.execute(
            text("INSERT INTO clinics (id, slug, name) VALUES (:c, 'p', 'P');"),
            {"c": str(clinic_id)},
        )
        result = await db_session.execute(
            text(
                "INSERT INTO patients (clinic_id, full_name) "
                "VALUES (:c, 'Pat 1'), (:c, 'Pat 2') RETURNING patient_code;"
            ),
            {"c": str(clinic_id)},
        )
        codes = [r.patient_code for r in result.all()]

    assert codes[0].startswith("DC-")
    assert codes[1].startswith("DC-")
    assert codes[0] != codes[1]
    assert int(codes[0].split("-")[-1]) + 1 == int(codes[1].split("-")[-1])


async def test_pgcrypto_round_trip_for_phi_column(db_session: AsyncSession) -> None:
    """phone_enc is stored encrypted but decrypts with the key."""
    async with db_session.begin():
        await db_session.execute(text("SET LOCAL row_security = off;"))
        clinic_id = uuid4()
        await db_session.execute(
            text("INSERT INTO clinics (id, slug, name) VALUES (:c, 'q', 'Q');"),
            {"c": str(clinic_id)},
        )
        await db_session.execute(
            text(
                "INSERT INTO patients (clinic_id, full_name, phone_enc) VALUES "
                "(:c, 'Phone Test', pgp_sym_encrypt('+91-9000000000', :k));"
            ),
            {"c": str(clinic_id), "k": "test-key"},
        )
        result = await db_session.execute(
            text(
                "SELECT pgp_sym_decrypt(phone_enc, :k) AS phone "
                "FROM patients WHERE full_name = 'Phone Test';"
            ),
            {"k": "test-key"},
        )
        phone = result.scalar_one()

    assert phone == "+91-9000000000"
