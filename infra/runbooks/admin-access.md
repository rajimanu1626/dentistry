# Admin Access Runbook

Create and manage clinic admin access safely in local, staging, and production.

## Role types

| Role | Scope | Can see patients? |
|---|---|---|
| `platform_admin` | All orgs/clinics/users (metadata) | **No** |
| `owner` / `dentist` / etc. | One clinic via `clinic_members` | Yes (within clinic) |

Platform operators use `/platform/*` APIs. Clinic staff use `/patients`, `/visits`, etc.

## 1) Local / Development

Use the built-in script to create or promote an owner for a clinic:

```bash
cd apps/api
uv run python -m app.db.create_admin \
  --email admin@example.com \
  --password 'StrongPass!123' \
  --clinic-id <clinic-uuid> \
  --full-name "Clinic Admin"
```

Notes:

- The script forces role to `owner` for that clinic.
- It writes local auth credentials via the same credential store used by `/auth/login`.
- It refuses to run in production unless `--allow-production` is explicitly set.

### Platform admin (not tied to any clinic)

```bash
cd apps/api
uv run python -m app.db.create_platform_admin \
  --email ops@example.com \
  --password 'StrongPass!123' \
  --full-name "Platform Ops"
```

Then login and use:

- `GET /platform/clinics` — list clinics (metadata only)
- `POST /platform/clinics` — create a clinic
- `POST /platform/groups` — create an organization (`clinic_groups`)
- `POST /platform/clinics/{clinic_id}/invites` — invite clinic owner/doctor
- `GET /platform/users` — list users (no patient PHI)

Platform accounts are blocked from `/patients`, `/visits`, `/media`, and sharing admin routes.

### Platform console (Phase 2 UI)

After login, platform-only users land on `/platform` with tabs for:

- **Clinics** — list clinics; admins can create clinics and issue owner invites
- **Organizations** — list/create `clinic_groups` (admin only)
- **Users** — list accounts; admins can activate/deactivate users

`platform_support` can view all platform tabs but cannot create or mutate (read-only).

```bash
# Create read-only platform support user
uv run python -m app.db.create_platform_admin \
  --email support@example.com \
  --password 'StrongPass!123' \
  --role platform_support \
  --full-name "Platform Support"
```

## 2) Production Standard Flow (Recommended)

Never create production admins via DB patching as a routine process.

1. Existing owner logs in.
2. Owner issues invite from `/settings/team` (or `POST /auth/invites` with `X-Clinic-Id`).
3. Invitee signs up using invite link.
4. Invite role determines access level (`owner` only when explicitly intended).

## 3) One-time First Owner Bootstrap (New Deployment)

When there are no users:

1. Temporarily allow controlled bootstrap (`SIGNUP_MODE=bootstrap` or first-user invite mode).
2. Create first owner through `/signup`.
3. Immediately set `SIGNUP_MODE=invite` after bootstrap.
4. Validate owner can open `/settings/team` and issue invites.

## 4) Break-glass Recovery (Production Emergency)

Use only when all owners are locked out.

1. Open an incident and require dual approval.
2. Run `create_admin` script in a controlled environment:

```bash
cd apps/api
uv run python -m app.db.create_admin \
  --email emergency-admin@example.com \
  --password '<strong-random-password>' \
  --clinic-id <clinic-uuid> \
  --full-name "Emergency Admin" \
  --allow-production
```

3. Confirm login and role on `/auth/me`.
4. Rotate password immediately after access is restored.
5. Audit and close incident.

## 5) Verification Checklist

- [ ] Admin can login at `/login`.
- [ ] `/auth/me` shows correct clinic membership and role.
- [ ] Admin can create/revoke invites.
- [ ] Access changes are recorded in audit logs / operational logs.

## 6) Security Requirements

- Use `SIGNUP_MODE=invite` in production.
- Keep `IDENTITY_PROVIDER=local` only where required; prefer managed IdP in production.
- Enforce strong password policy and MFA at IdP layer where available.
- Rotate secrets according to `infra/runbooks/rotate-keys.md`.
- Never add `platform_admin` users to `clinic_members` for routine ops — that would grant PHI access.
- Map production platform admins to a dedicated IdP group (e.g. `PlatformOps`) in a later phase.
