"""Create or update a clinic admin user for local/dev operations.

Usage:
    uv run python -m app.db.create_admin \
      --email admin@example.com \
      --password 'StrongPass!123' \
      --clinic-id <uuid> \
      --full-name "Clinic Admin"

By default this command refuses to run in production.
"""

from __future__ import annotations

import asyncio
from argparse import ArgumentParser, Namespace
from uuid import UUID, uuid4

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import get_session_factory, reset_engine
from app.models import Clinic, ClinicMember, ClinicRole, User
from app.services.auth import store_password_for_local


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Create/update a local clinic admin user.")
    parser.add_argument("--email", required=True, help="Admin email.")
    parser.add_argument("--password", required=True, help="Admin password.")
    parser.add_argument("--clinic-id", required=True, help="Clinic UUID.")
    parser.add_argument("--full-name", default="Clinic Admin", help="Display full name.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Allow execution in production (break-glass only).",
    )
    return parser


async def _run(args: Namespace) -> None:
    settings = get_settings()
    if settings.is_production and not args.allow_production:
        raise SystemExit(
            "Refusing to run in production without --allow-production (break-glass)."
        )
    if len(args.password) < 10:
        raise SystemExit("Password must be at least 10 characters.")

    clinic_id = UUID(args.clinic_id)
    await reset_engine()
    factory = get_session_factory()

    async with factory() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL row_security = off;"))
            clinic_row = await session.execute(select(Clinic).where(Clinic.id == clinic_id))
            clinic = clinic_row.scalar_one_or_none()
            if clinic is None:
                raise SystemExit(f"Clinic not found: {clinic_id}")

            user_row = await session.execute(select(User).where(User.email == args.email))
            user = user_row.scalar_one_or_none()
            if user is None:
                user = User(
                    id=uuid4(),
                    email=args.email,
                    full_name=args.full_name,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
            elif args.full_name and user.full_name != args.full_name:
                user.full_name = args.full_name

            member_row = await session.execute(
                select(ClinicMember).where(
                    ClinicMember.clinic_id == clinic_id,
                    ClinicMember.user_id == user.id,
                )
            )
            member = member_row.scalar_one_or_none()
            if member is None:
                session.add(
                    ClinicMember(
                        clinic_id=clinic_id,
                        user_id=user.id,
                        role=ClinicRole.OWNER,
                    )
                )
            else:
                member.role = ClinicRole.OWNER

        store_password_for_local(args.email, user.id, args.password)

    print("Admin account is ready:")
    print(f"- email: {args.email}")
    print(f"- clinic_id: {clinic_id}")
    print(f"- role: owner")


def main() -> None:
    args = _build_parser().parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
