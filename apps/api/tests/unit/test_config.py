"""Smoke tests for application configuration."""

from __future__ import annotations

from app.core.config import Settings


def test_defaults_load() -> None:
    s = Settings()
    assert s.app_name == "clinic-crm"
    assert s.app_env in {"development", "test", "staging", "production"}


def test_cors_origins_list_splits() -> None:
    s = Settings(cors_allowed_origins="http://a.com, http://b.com ,http://c.com")
    assert s.cors_origins_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_is_production_flag() -> None:
    assert Settings(app_env="production").is_production
    assert not Settings(app_env="development").is_production
