# Local Troubleshooting

Use this checklist when auth, API reachability, or patient saves fail in local Docker workflows.

## 1) Verify stack health

```bash
bun run compose:up
docker compose -f infra/compose/docker-compose.yml ps
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:5173
```

- If API is down, inspect `api` logs first.
- If web is up but API calls fail, verify the web container can resolve `api:8000`.

## 2) If web shows "API unreachable"

- Confirm `VITE_API_BASE_URL` in compose is `http://api:8000` for the `web` service.
- Confirm frontend requests are going through `/api` proxy in dev mode.
- Restart only web and api:

```bash
docker compose -f infra/compose/docker-compose.yml restart web api
```

## 3) If login/invite suddenly fails

- Check `SIGNUP_MODE` and invite policy:

```bash
curl -fsS http://localhost:8000/auth/config
```

- Verify owner is sending `X-Clinic-Id` when creating/listing/revoking invites.
- For local identity mode, use `/settings/security` to rotate passwords if credentials changed.

## 4) If patient create/update fails

- Ensure every patient endpoint includes `X-Clinic-Id`.
- Re-run integration regression tests:

```bash
cd apps/api
uv run pytest tests/integration/test_auth_signup_policy.py -q
```

## 5) Reset local state (last resort)

```bash
bun run compose:down
bun run compose:up
bun run db:migrate
```

This resets Docker volumes and local Postgres data.
