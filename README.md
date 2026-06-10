# dentistry

CRM for medical clinics and hospitals — multi-tenant dental clinic CRM & dashboard.

- **Frontend:** React 19 + Vite + TanStack Router/Query + Tailwind + shadcn/ui (bun)
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (uv)
- **Database:** Postgres 16 (Supabase prod; local Postgres in dev) with Row-Level Security
- **Storage:** Supabase Storage / S3-compatible (MinIO locally)
- **Auth:** Supabase Auth in prod, local JWT in dev — swappable via `IDENTITY_PROVIDER`
- **Compliance:** designed for India DPDP (encryption at rest + transit, audit log, ap-south-1 hosting)

> See [`CLAUDE.md`](CLAUDE.md) for the architecture invariants and contributor handbook.

---

## Prerequisites

- **bun** ≥ 1.1 — <https://bun.sh>
- **uv** ≥ 0.10 — <https://docs.astral.sh/uv/>
- **Docker Desktop** (or Docker Engine + Compose v2)
- **Python** 3.13 (auto-installed by uv if missing)
- **Node** 20+ (used by some web dev tooling; bun provides the runtime)

```bash
# install bun
curl -fsSL https://bun.sh/install | bash

# install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Sign in

1. Open [http://localhost:5173/signup](http://localhost:5173/signup) on a **fresh database** to create the first clinic owner (`SIGNUP_MODE=invite` allows bootstrap when no users exist).
2. After that, new users need an **invite** from a clinic owner (`POST /auth/invites` with `X-Clinic-Id`) and should open `/signup?token=…&email=…`.
3. Sign in at [http://localhost:5173/login](http://localhost:5173/login).
4. Owners can manage invites at `/settings/team`; users can change password at `/settings/security`.

Public signup that creates arbitrary new clinics is blocked unless `SIGNUP_MODE=open` (dev only).

## First-time setup

```bash
git clone <repo> clinic-crm
cd clinic-crm

cp .env.example .env

bun install
cd apps/api && uv sync && cd ../..

bun run compose:up

bun run db:migrate
```

The frontend will be at <http://localhost:5173>, the API at <http://localhost:8000>,
MinIO console at <http://localhost:9001>, and mailhog at <http://localhost:8025>.

## Common commands

| Command | What it does |
|---|---|
| `bun run dev:api` | Run the FastAPI dev server (hot reload) |
| `bun run dev:web` | Run the Vite dev server |
| `bun run compose:up` | Bring up Postgres + MinIO + mailhog + api + web |
| `bun run compose:down` | Tear it down (and wipe volumes) |
| `bun run db:migrate` | Apply Alembic migrations |
| `bun run db:revision -- "add patients"` | Create a new auto-generated migration |
| `bun run test:api` | Run pytest (with testcontainers Postgres) |
| `bun run test:web` | Run Vitest |
| `bun run test:e2e` | Run Playwright against the docker-compose stack |
| `bun run lint` | Biome + Ruff |
| `bun run portability:check` | Verify portability invariants |

## Monorepo layout

```
clinic-crm/
├── apps/
│   ├── web/                # React + Vite frontend
│   └── api/                # FastAPI backend
├── packages/
│   └── shared-types/       # TS types generated from FastAPI OpenAPI
├── infra/
│   ├── docker/             # Per-service Dockerfiles
│   ├── compose/            # docker-compose.yml for local dev
│   ├── fly/                # Fly.io deploy config (deploy-only)
│   ├── aws/                # Terraform stubs for future RDS+ECS migration
│   ├── runbooks/           # restore-db.md, migrate-to-aws.md, rotate-keys.md
│   └── db/                 # SQL fixtures, RLS policies, seed scripts
├── .github/workflows/      # CI/CD
├── .cursor/                # Project rules & hooks for the AI assistant
├── scripts/                # Tooling scripts (portability check, etc.)
├── CLAUDE.md               # Architecture + invariants
├── biome.json
├── package.json            # bun workspaces root
└── README.md
```

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — architecture, security & portability invariants
- [`infra/runbooks/restore-db.md`](infra/runbooks/restore-db.md) — backup / restore
- [`infra/runbooks/migrate-to-aws.md`](infra/runbooks/migrate-to-aws.md) — Supabase → AWS playbook
- [`infra/runbooks/rotate-keys.md`](infra/runbooks/rotate-keys.md) — PHI key & secret rotation
- [`infra/runbooks/local-troubleshooting.md`](infra/runbooks/local-troubleshooting.md) — quick recovery path for common local failures
- [`infra/runbooks/admin-access.md`](infra/runbooks/admin-access.md) — admin bootstrap, invite flow, and break-glass recovery

## License

Proprietary — all rights reserved.
