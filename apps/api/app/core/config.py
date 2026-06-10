"""Application configuration loaded from environment variables.

Every external endpoint and credential is env-driven so the stack stays portable
(Supabase -> AWS RDS/Cognito/S3). See ``CLAUDE.md`` for the portability invariants.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "test", "staging", "production"]
IdentityProvider = Literal["local", "supabase", "cognito"]
SignupMode = Literal["closed", "invite", "bootstrap", "open"]


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "development"
    app_name: str = "clinic-crm"
    app_base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://crm:crm@localhost:5432/crm",
        description="Async SQLAlchemy URL.",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://crm:crm@localhost:5432/crm",
        description="Sync URL used by Alembic.",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 5

    identity_provider: IdentityProvider = "local"
    jwt_issuer: str = "clinic-crm-local"
    jwt_audience: str = "clinic-crm"
    jwt_signing_key: SecretStr = SecretStr("change-me-in-prod-use-32-byte-random")
    jwt_access_token_ttl_seconds: int = 15 * 60
    jwt_refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60
    jwks_url: str | None = None
    jwks_cache_ttl_seconds: int = 3600

    s3_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "clinic-crm-dev"
    s3_access_key: SecretStr = SecretStr("minio")
    s3_secret_key: SecretStr = SecretStr("miniominio")
    s3_public_base_url: str | None = None
    s3_signed_url_ttl_seconds: int = 60
    s3_force_path_style: bool = True

    phi_encryption_key: SecretStr = SecretStr("replace-with-base64-32-bytes")
    external_share_hmac_secret: SecretStr = SecretStr("replace-with-base64-32-bytes")
    cors_allowed_origins: str = "http://localhost:5173"

    external_share_default_ttl_seconds: int = 24 * 60 * 60
    external_share_max_ttl_seconds: int = 7 * 24 * 60 * 60
    external_share_max_views: int = 5
    external_share_max_password_attempts: int = 5

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str = "no-reply@clinic-crm.local"
    smtp_use_tls: bool = False

    rate_limit_storage_uri: str = "memory://"

    # Signup policy (see ``app/services/auth.py``).
    # - closed: no self-service signup
    # - invite: join via clinic invite; bootstrap allowed when DB has zero users
    # - bootstrap: signup only while the users table is empty (first clinic owner)
    # - open: public signup (creates a new clinic) — dev-only
    signup_mode: SignupMode = "invite"
    invite_default_ttl_seconds: int = 7 * 24 * 60 * 60
    invite_token_hmac_secret: SecretStr | None = None

    @property
    def invite_hmac_secret_value(self) -> str:
        """HMAC key for clinic invite tokens (falls back to external-share secret)."""
        if self.invite_token_hmac_secret is not None:
            return self.invite_token_hmac_secret.get_secret_value()
        return self.external_share_hmac_secret.get_secret_value()

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings. Override via ``Settings()`` in tests."""
    return Settings()
