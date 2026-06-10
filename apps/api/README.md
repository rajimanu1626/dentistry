# clinic-crm-api

FastAPI backend.

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
uv run mypy app
```

Module layout:

- `app/core/` — config, logging, errors
- `app/db/` — engine, session, RLS context (phase 2)
- `app/models/` — SQLAlchemy ORM (phase 2)
- `app/schemas/` — Pydantic DTOs
- `app/routers/` — HTTP routers
- `app/services/` — business logic
- `app/adapters/identity/` — JWT validation against `local` / `supabase` / `cognito`
- `app/adapters/storage/` — S3-compatible object storage
- `app/sharing/` — internal + external patient sharing (phase 7)
- `app/middleware/` — request id, auth, RLS, security headers
- `app/templates/` — Jinja2 templates (Rx PDF, share landing page)

All provider-specific imports stay inside `app/adapters/*`; the rest of the code
must remain provider-agnostic. See [`../../CLAUDE.md`](../../CLAUDE.md) for invariants.
