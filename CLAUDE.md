# CLAUDE.md — clinic-crm contributor handbook

> Read this top-to-bottom once. Bookmark the *Security invariants* and
> *Portability invariants* sections; they're the load-bearing parts.

## What this is

A multi-tenant dental clinic CRM. One install, many clinics, many doctors,
all PHI-bearing. Designed for India DPDP residency (Mumbai region, ap-south-1)
with a free-tier-first stack (Supabase + Fly.io + Cloudflare Pages) and a
documented **half-day migration path to AWS** (RDS + Cognito + S3 + ECS).

## Stack

| Layer | What | Why |
|---|---|---|
| Frontend | React 19 + Vite + TanStack Router/Query + Tailwind + shadcn/ui (bun) | Modern DX, file-based routes, no Redux |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (uv) | Type-safe, async, well-tooled |
| DB | Postgres 16 (Supabase prod, local in dev) | RLS for multi-tenancy |
| Storage | S3-compatible (MinIO dev, Supabase Storage prod) via `boto3` | One SDK, every provider |
| Auth | `IDENTITY_PROVIDER` env: `local` (dev) / `supabase` (prod) / `cognito` (AWS) | JWT validated via JWKS |
| PDF | WeasyPrint + Jinja2 | Server-side, deterministic |
| Container | per-service Dockerfile, docker-compose for dev | Hot reload + parity |
| CI | GitHub Actions | pr.yml, e2e.yml, build-and-publish.yml, deploy.yml, nightly-backup.yml |

## Repo map

```
clinic-crm/
├── apps/
│   ├── api/            # FastAPI
│   │   ├── app/
│   │   │   ├── adapters/{identity,storage}/   # provider seams
│   │   │   ├── core/                          # config, logging, errors, security
│   │   │   ├── db/                            # base, session, RLS context, seed
│   │   │   ├── middleware/                    # auth dependency
│   │   │   ├── models/                        # SQLAlchemy ORM
│   │   │   ├── routers/                       # FastAPI routers
│   │   │   ├── schemas/                       # Pydantic DTOs
│   │   │   ├── services/                      # business logic
│   │   │   └── sharing/                       # internal + external sharing
│   │   ├── alembic/                           # migrations
│   │   └── tests/{unit,integration,rls,sharing}
│   └── web/            # React + Vite
├── packages/shared-types/
├── infra/
│   ├── docker/         # api / web Dockerfiles (prod & dev)
│   ├── compose/        # docker-compose.yml
│   ├── fly/            # fly.toml
│   ├── aws/            # Terraform stubs (RDS, ECS, S3, Cognito, VPC)
│   ├── runbooks/       # restore-db.md, migrate-to-aws.md, rotate-keys.md
│   └── db/             # init SQL (extensions, roles)
├── .github/workflows/
├── .cursor/{rules,hooks,skills}/
├── scripts/check_portability.py
└── docs/env-contract.md
```

## Domain model (high level)

- `clinic_groups` — chain / parent org (many clinics roll up here).
- `clinics` — the tenant boundary. Carries settings + a per-clinic
  `patient_code_sequence` for the human-readable `DC-YYYY-NNNNN` code.
- `users` — local mirror of the IdP user (never FK to `auth.users`).
- `clinic_members` — `(clinic_id, user_id, role)`.
- `patients` — clinical record. PHI columns are `bytea` `pgp_sym_encrypt` blobs.
- `visits` — per-encounter notes; FKs patient + dentist.
- `prescription_templates` — per-clinic Jinja2 HTML.
- `prescriptions` — Rx items as `jsonb`, optionally pointing at a template.
- `patient_media` — `before`/`after`/`xray` images; bytes live in object storage.
- `patient_shares` — internal doctor-to-doctor grants (with `expires_at`, `revoked_at`).
- `external_share_links` — out-of-platform share (HMAC-stored token + argon2
  password + view/attempt counters + expiry).
- `audit_log` — append-only history of every mutation + critical app event.

## Security invariants

Pinned in `.cursor/rules/security-invariants.mdc` (always-on). The short list:

1. **Every tenant table has `clinic_id` + RLS policy + audit trigger.** Use
   `.cursor/skills/add-tenant-table/SKILL.md`.
2. **Never query a tenant table without an RLS context set.** The auth
   dependency does this for you (`SET LOCAL app.current_user_id`).
3. **Never log PHI.** A redactor in `app/core/logging.py` strips common keys
   but it's a safety net, not a license.
4. **PHI columns store ciphertext only** (`pgp_sym_encrypt`). Decrypt at the
   service layer; never write plaintext.
5. **All mutations are audited.** Triggers cover the DDL; the app emits
   explicit rows for logins, exports, share lifecycle.
6. **TLS + HSTS + CSP** are configured in `infra/docker/nginx.conf`. Don't
   loosen.
7. **External share links** must HMAC the token, argon2 the password, lock
   after 5 failed attempts, watermark every rendered PDF, and rate-limit the
   unlock endpoint to 10/min.

## Portability invariants

Pinned in `.cursor/rules/portability-invariants.mdc` (always-on) and
enforced by `scripts/check_portability.py` (CI + the `afterFileEdit` hook).

1. **RLS uses session variables, never `auth.uid()`.** Policies reference
   `current_setting('app.current_user_id')::uuid`.
2. **Own the user identity table.** No FK to `auth.users`.
3. **JWT validation via `JWKS_URL`** — change the env var, change the provider.
4. **Object storage via plain S3 SDK.** `boto3` + env-driven endpoint.
5. **No Supabase-only features.** Banned: Realtime, Edge Functions, Storage
   RLS policies, `auth.*`, `pg_net`, `pg_cron`.
6. **Strict 12-factor config.** All hosts/secrets via env vars.
7. **Container is the unit of deploy.** Dockerfile is identical on Fly and ECS.
8. **`app/adapters/{identity,storage}/`** holds every provider-specific import.

See [`infra/runbooks/migrate-to-aws.md`](infra/runbooks/migrate-to-aws.md) for
the step-by-step Supabase → AWS playbook.

## Day-to-day commands

```bash
make install            # bun + uv sync
make compose-up         # full dev stack (postgres + minio + mailhog + api + web)
make db-migrate         # alembic upgrade head
make db-revision m="add appointments"
make test               # api + web
make portability        # python3 scripts/check_portability.py
make lint               # ruff + biome
```

## How to add things

| Task | Where |
|---|---|
| New tenant table | `.cursor/skills/add-tenant-table/SKILL.md` |
| New API endpoint | Add router under `app/routers/`, register in `app/main.py` |
| New domain model | `app/models/tables.py`, re-export from `app/models/__init__.py`, then migration |
| New env var | `app/core/config.py` + `.env.example` + `docs/env-contract.md` |
| New IdP | Sibling module in `app/adapters/identity/`, switch in `get_identity_provider()` |
| New storage backend | Sibling module in `app/adapters/storage/`, switch in `get_storage()` |
| Rotate PHI key | `infra/runbooks/rotate-keys.md` |
| Restore from backup | `infra/runbooks/restore-db.md` |
| Migrate to AWS | `infra/runbooks/migrate-to-aws.md` |

## Testing

- **Unit**: `tests/unit/*` — pure logic, no DB. Lightning fast.
- **Integration**: `tests/integration/*` — testcontainers-postgres, runs the
  real Alembic migrations.
- **RLS**: `tests/rls/*` — explicit isolation tests; two clinics, two users.
- **Sharing**: `tests/sharing/*` — internal/external lifecycle, lockout,
  expiry, audit.
- **Frontend**: `apps/web/tests/*` with Vitest + RTL + MSW.
- **E2E**: `apps/web/playwright/*` against the docker-compose stack.
- **API contract**: `schemathesis` is wired in; runs in CI.

Coverage targets (advisory, not gate): 80% on `app/services`, `app/sharing`,
`app/core`. The RLS test module is mandatory.

## Free-tier limits & alerting thresholds

| Service | Limit | Alert at |
|---|---|---|
| Supabase Postgres | 500 MB DB / 2 GB egress | 70% |
| Supabase Storage | 1 GB | 70% |
| Supabase MAU | 50_000 | 70% |
| Fly.io shared CPU | 3 × shared-cpu-1x@256MB | n/a (single machine) |
| Cloudflare Pages | 500 builds/mo | 80% |
| Backblaze B2 / R2 backups | 10 GB free tier | 70% |

When two of the above cross 70% in the same week, plan the move to AWS.

## Contact + glossary

- **PHI** — Protected Health Information. Anything that identifies a patient
  or their care.
- **DPDP** — India's Digital Personal Data Protection Act, 2023.
- **RLS** — Postgres Row-Level Security.
- **JWKS** — JSON Web Key Set; an IdP-hosted URL that lists the keys we
  validate JWTs with.
