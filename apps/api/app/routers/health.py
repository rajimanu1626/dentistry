"""Health and readiness endpoints. Public; no auth."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"]
    version: str
    service: str = "clinic-crm-api"


@router.get("/healthz", response_model=Health)
async def healthz() -> Health:
    """Liveness probe."""
    return Health(status="ok", version=__version__)


@router.get("/readyz", response_model=Health)
async def readyz() -> Health:
    """Readiness probe. Will validate downstream deps in later phases."""
    return Health(status="ok", version=__version__)
