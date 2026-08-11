> This file is the same as [`CLAUDE.md`](CLAUDE.md). Some agent harnesses look
> for `AGENTS.md` by convention; rather than duplicate the content, point them at
> the canonical handbook.

See [`CLAUDE.md`](CLAUDE.md).

## Cursor Cloud specific instructions

Durable, non-obvious notes for running this repo in the Cursor Cloud VM. Standard
commands live in [`README.md`](README.md) / [`CLAUDE.md`](CLAUDE.md) / `Makefile`;
only the caveats are repeated here.

### Toolchain / environment
- `bun` (`~/.bun/bin`) and `uv` (`~/.local/bin`) are installed and on `PATH` via
  `~/.bashrc`. `uv` provisions Python 3.13 for the API (system `python3` is 3.12).
- Docker is installed for Docker-in-Docker: storage driver `fuse-overlayfs` and
  the containerd snapshotter disabled in `/etc/docker/daemon.json` (required for
  Docker 29 + fuse-overlayfs), and `iptables`/`ip6tables` set to legacy.
- The startup update script only refreshes deps (`bun install`, `uv sync`); it
  does NOT start any services.

### Starting the dev stack (`make compose-up`)
- There is no systemd, so the Docker daemon does not auto-start. Start it once
  per VM before any Docker/compose command: `sudo dockerd > /tmp/dockerd.log 2>&1 &`
  (a long-running process — run it in a tmux session, not a one-shot job).
- `docker`/`docker compose` need root here; either prefix with `sudo` or run
  `sudo chmod 666 /var/run/docker.sock` once so the `ubuntu` user (and host-run
  `pytest` testcontainers) can reach the daemon.
- The compose `api` service reads `env_file: ../../.env`, so a repo-root `.env`
  must exist (copy from `.env.example`). Fill real values for
  `PHI_ENCRYPTION_KEY`, `EXTERNAL_SHARE_HMAC_SECRET`, `JWT_SIGNING_KEY`. For local
  end-user testing set `SIGNUP_MODE=open` so `/signup` can bootstrap the first
  clinic without an invite.
- Migrations are NOT auto-run by the api container. After the stack is up, run
  `make db-migrate` from the host (uses `DATABASE_URL_SYNC` → `localhost:5432`).
- URLs: web `http://localhost:5173`, API `http://localhost:8000` (`/docs`,
  `/healthz`), MinIO console `http://localhost:9001`, MailHog `http://localhost:8025`.

### Gotchas
- Signup/email validation rejects reserved TLDs (`.test`, `.example`, `.local`,
  `example.com`). Use a normal-looking domain (e.g. `@brightsmile.com`) for demo
  accounts.
- Web unit tests: `bun run test:web` / `make test-web` fail because the `test`
  script hardcodes `node ../../node_modules/vitest/...`, but the current `bun`
  installs `vitest` workspace-locally. Run them with
  `cd apps/web && node node_modules/vitest/vitest.mjs run` instead.
- API tests (`make test-api`) need the Docker daemon running (testcontainers
  spins up `postgres:16-alpine`).

### Known pre-existing failures (not environment issues)
- 6 tests in `apps/api/tests/rls/test_rls_patient_isolation.py` fail: the shared
  `_seed_two_clinics` helper inserts a `clinic_members` row before the matching
  `clinics` row exists (non-deferrable FK), so they fail deterministically. The
  other 39 API tests pass.
- `ruff check` (7) and `biome check` (~29) report pre-existing lint findings in
  committed code; the lint tooling itself runs correctly.
