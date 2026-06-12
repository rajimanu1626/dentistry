# Environment-variable contract

This file is the **source of truth** for which env vars the application
expects. Adding/removing/renaming any var requires updating:

1. `apps/api/app/core/config.py` (the `Settings` model)
2. `.env.example`
3. This file
4. Any of `infra/fly/fly.toml`, `infra/aws/*.tf`, `.github/workflows/*.yml` that
   reference it

The CI workflow `pr.yml` does **not** strictly enforce sync yet, but the
portability check in `scripts/check_portability.py` lives alongside.

## Categories

### App

| Var | Default | Required? | Notes |
|---|---|---|---|
| `APP_ENV` | `development` | yes | one of `development`, `test`, `staging`, `production` |
| `APP_NAME` | `clinic-crm` | no | |
| `APP_BASE_URL` | `http://localhost:5173` | yes | used to build external share URLs |
| `API_BASE_URL` | `http://localhost:8000` | yes | used by web `vite.config.ts` proxy |
| `LOG_LEVEL` | `INFO` | no | |

### Database

| Var | Required? | Provider examples |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+asyncpg://...` — Supabase / RDS / local |
| `DATABASE_URL_SYNC` | yes | `postgresql+psycopg://...` — for Alembic |
| `DATABASE_POOL_SIZE` | no | default 10 |
| `DATABASE_MAX_OVERFLOW` | no | default 5 |

### Identity (portable)

| Var | Notes |
|---|---|
| `IDENTITY_PROVIDER` | `local` (dev) / `supabase` / `cognito` |
| `JWT_ISSUER` | issuer claim — pool URL on Cognito, project URL on Supabase |
| `JWT_AUDIENCE` | audience claim — client_id on Cognito, project on Supabase |
| `JWT_SIGNING_KEY` | **local only** — HS256 signing key |
| `JWKS_URL` | required when `IDENTITY_PROVIDER` ≠ `local` |
| `JWKS_CACHE_TTL_SECONDS` | default 3600 |
| `JWT_ACCESS_TOKEN_TTL_SECONDS` | default 900 |
| `JWT_REFRESH_TOKEN_TTL_SECONDS` | default 2_592_000 |

### Object storage (portable S3 interface)

| Var | Notes |
|---|---|
| `S3_ENDPOINT` | MinIO `http://localhost:9000`, Supabase `https://<p>.supabase.co/storage/v1/s3`, AWS `https://s3.<region>.amazonaws.com` |
| `S3_REGION` | any string for MinIO; real AWS region for S3 |
| `S3_BUCKET` | name only, no leading `s3://` |
| `S3_ACCESS_KEY` | |
| `S3_SECRET_KEY` | |
| `S3_FORCE_PATH_STYLE` | `true` for MinIO/Supabase, `false` for AWS |
| `S3_SIGNED_URL_TTL_SECONDS` | default 60 |
| `S3_PUBLIC_BASE_URL` | optional; if set, the API may return it for public objects (avoid for PHI) |

### Security

| Var | Notes |
|---|---|
| `PHI_ENCRYPTION_KEY` | pgcrypto symmetric key. Rotate via `infra/runbooks/rotate-keys.md` |
| `EXTERNAL_SHARE_HMAC_SECRET` | HMAC key for share tokens. Rotation kills outstanding links — see runbook |
| `CORS_ALLOWED_ORIGINS` | comma-separated origins |

### Sharing limits

| Var | Default |
|---|---|
| `EXTERNAL_SHARE_DEFAULT_TTL_SECONDS` | 86400 (24h) |
| `EXTERNAL_SHARE_MAX_TTL_SECONDS` | 604800 (7d) |
| `EXTERNAL_SHARE_MAX_VIEWS` | 5 |
| `EXTERNAL_SHARE_MAX_PASSWORD_ATTEMPTS` | 5 |

### Email

| Var | Notes |
|---|---|
| `SMTP_HOST` | mailhog locally, SES/Postmark/etc in prod |
| `SMTP_PORT` | |
| `SMTP_USER` | optional |
| `SMTP_PASSWORD` | optional |
| `SMTP_FROM_EMAIL` | |
| `SMTP_USE_TLS` | |

### Rate limit

| Var | Notes |
|---|---|
| `RATE_LIMIT_STORAGE_URI` | `memory://` for single-instance, `redis://...` for multi |

## Provider matrices

Switching providers is **only** an env-var change:

| Capability | Local dev | Supabase prod | AWS prod |
|---|---|---|---|
| Identity | `IDENTITY_PROVIDER=local` + `JWT_SIGNING_KEY` | `=supabase` + `JWKS_URL=<project>.supabase.co/auth/v1/keys` | `=cognito` + Cognito JWKS |
| DB | `postgres:16-alpine` via compose | Supabase Postgres | RDS Postgres 16 |
| Storage | MinIO via compose | Supabase Storage (S3 endpoint) | AWS S3 |
| Mail | mailhog | SES / SendGrid | SES |

No code changes between columns — only env values. That's the whole point of
this contract.
