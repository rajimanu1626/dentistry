"""Create or update a platform admin (no clinic membership, no PHI access).

Usage:
    uv run python -m app.db.create_platform_admin \
      --email ops@example.com \
      --password 'StrongPass!123' \
      --full-name "Platform Ops"
"""

from __future__ import annotations

import asyncio
from argparse import ArgumentParser, Namespace
from uuid import uuid4

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import get_session_factory, reset_engine
from app.models import User
from app.models.enums import SystemRole
from app.services.auth import store_password_for_local


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Create/update a platform admin user.")
    parser.add_argument("--email", required=True, help="Platform admin email.")
    parser.add_argument("--password", required=True, help="Platform admin password.")
    parser.add_argument("--full-name", default="Platform Admin", help="Display full name.")
    parser.add_argument(
        "--role",
        choices=[SystemRole.PLATFORM_ADMIN.value, SystemRole.PLATFORM_SUPPORT.value],
        default=SystemRole.PLATFORM_ADMIN.value,
        help="Platform role (default: platform_admin).",
    )
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

    role = SystemRole(args.role)
    await reset_engine()
    factory = get_session_factory()

    async with factory() as session:
        async with session.begin():
            await session.execute(text("SET LOCAL row_security = off;"))
            row = await session.execute(select(User).where(User.email == args.email))
            user = row.scalar_one_or_none()
            if user is None:
                user = User(
                    id=uuid4(),
                    email=args.email,
                    full_name=args.full_name,
                    system_role=role,
                    is_active=True,
                )
                session.add(user)
                await session.flush()
            else:
                user.system_role = role
                user.full_name = args.full_name
                user.is_active = True

        store_password_for_local(args.email, user.id, args.password)

    print("Platform admin account is ready:")
    print(f"- email: {args.email}")
    print(f"- user_id: {user.id}")
    print(f"- system_role: {role.value}")
    print("- clinic_memberships: none (by design)")


def main() -> None:
    args = _build_parser().parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
