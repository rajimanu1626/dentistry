"""Seed local Postgres with demo clinic data and test patients.

Run with ``uv run python -m app.db.seed`` after ``alembic upgrade head``.
Intended for development only.
"""

from __future__ import annotations

import asyncio
from argparse import ArgumentParser, Namespace
from datetime import date
from uuid import uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory, reset_engine
from app.services.pdf import DEFAULT_PRESCRIPTION_TEMPLATE_HTML


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Seed local development database.")
    parser.add_argument(
        "--patients",
        type=int,
        default=1,
        help="Number of patients to seed (default: 1).",
    )
    parser.add_argument(
        "--clinic-id",
        type=str,
        default=None,
        help="Existing clinic id to seed patients into (optional).",
    )
    return parser


async def main(args: Namespace) -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Refusing to seed a production database.")
    if args.patients < 1:
        raise SystemExit("--patients must be >= 1.")

    await reset_engine()
    factory = get_session_factory()
    seeded_clinic_id = args.clinic_id
    seeded_owner_id: str | None = None
    key = settings.phi_encryption_key.get_secret_value()

    async with factory() as session, session.begin():
        await session.execute(text("SET LOCAL row_security = off;"))

        if seeded_clinic_id is None:
            user_id = uuid4()
            clinic_id = uuid4()
            seeded_clinic_id = str(clinic_id)
            seeded_owner_id = str(user_id)
            await session.execute(
                text("INSERT INTO users (id, email, full_name) VALUES (:i, :e, :n);"),
                {"i": seeded_owner_id, "e": "owner@demo.test", "n": "Dr. Demo"},
            )
            await session.execute(
                text(
                    "INSERT INTO clinics (id, slug, name, address) "
                    "VALUES (:i, 'demo', 'Demo Dental', '1 Main St, Mumbai');"
                ),
                {"i": seeded_clinic_id},
            )
            await session.execute(
                text(
                    "INSERT INTO clinic_members (clinic_id, user_id, role) "
                    "VALUES (:c, :u, 'owner');"
                ),
                {"c": seeded_clinic_id, "u": seeded_owner_id},
            )
            await session.execute(
                text(
                    "INSERT INTO prescription_templates "
                    "(clinic_id, name, html_template, is_default) "
                    "VALUES (:c, 'default', :h, true);"
                ),
                {"c": seeded_clinic_id, "h": DEFAULT_PRESCRIPTION_TEMPLATE_HTML.strip()},
            )

        for i in range(args.patients):
            sex = "M" if i % 2 == 0 else "F"
            day = (i % 28) + 1
            month = (i % 12) + 1
            year = 1970 + (i % 40)
            await session.execute(
                text(
                    """
                    INSERT INTO patients (
                        clinic_id,
                        full_name,
                        date_of_birth,
                        sex,
                        phone_enc,
                        notes
                    )
                    VALUES (
                        :clinic_id,
                        :full_name,
                        :dob,
                        :sex,
                        pgp_sym_encrypt(CAST(:phone AS text), CAST(:key AS text)),
                        :notes
                    );
                    """
                ),
                {
                    "clinic_id": seeded_clinic_id,
                    "full_name": f"Test Patient {i + 1:03d}",
                    "dob": date(year, month, day),
                    "sex": sex,
                    "phone": f"900000{i + 1:04d}",
                    "notes": "Bulk-seeded for list/search testing.",
                    "key": key,
                },
            )

    print(
        f"Seeded {args.patients} patients into clinic={seeded_clinic_id}"
        + (f" owner={seeded_owner_id}" if seeded_owner_id else "")
    )


if __name__ == "__main__":
    parsed = _build_parser().parse_args()
    asyncio.run(main(parsed))
