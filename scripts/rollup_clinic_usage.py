#!/usr/bin/env python3
"""Roll up per-clinic usage snapshots for platform billing analytics."""

from __future__ import annotations

import asyncio
import os
import sys


async def _main() -> int:
    os.environ.setdefault("APP_ENV", "production")
    from app.core.config import get_settings
    from app.db.session import get_session_factory, reset_engine
    from app.services import platform_usage as usage_service

    get_settings.cache_clear()
    await reset_engine()
    factory = get_session_factory()
    async with factory() as session:
        result = await usage_service.rollup_all_clinics(session)
    print(
        f"Rolled up usage for {result.clinics_processed} clinics "
        f"on {result.snapshot_date.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
