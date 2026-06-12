# Restore from nightly backup

Backups are encrypted `pg_dump --format=custom` files stored in the B2/R2 bucket
configured by `BACKUP_S3_*` secrets. Each filename is
`clinic-crm-<YYYYMMDDTHHMMSSZ>.dump.gpg`. Retention: 30 days (lifecycle rule).

## Prerequisites

- `gpg` with the **private key** corresponding to `BACKUP_GPG_RECIPIENT`.
- `aws` CLI configured with `BACKUP_S3_*` credentials (read-only is enough).
- `psql` + `pg_restore` matching the prod Postgres major version (currently 16).
- Either a clean **Supabase branch DB** (preferred — non-destructive) or a brand-new
  RDS / local Postgres instance.

## 1. Pick a snapshot and download it

```bash
aws s3 ls --endpoint-url "$BACKUP_S3_ENDPOINT" s3://$BACKUP_S3_BUCKET/ | sort
aws s3 cp --endpoint-url "$BACKUP_S3_ENDPOINT" \
  s3://$BACKUP_S3_BUCKET/clinic-crm-20260527T183000Z.dump.gpg ./snap.dump.gpg
```

## 2. Decrypt

```bash
gpg --decrypt snap.dump.gpg > snap.dump
```

## 3. Restore into a target DB

The dump is plain Postgres with `--no-owner --no-acl`, so it restores fine into
any Postgres 16 instance:

```bash
createdb -h $TARGET_HOST -U $TARGET_ADMIN clinic_restored
pg_restore -h $TARGET_HOST -U $TARGET_ADMIN -d clinic_restored \
  --no-owner --no-acl --jobs=4 ./snap.dump
psql -h $TARGET_HOST -U $TARGET_ADMIN -d clinic_restored \
  -f infra/db/init/00-extensions.sql \
  -f infra/db/init/10-roles.sql
```

## 4. Apply Alembic to make sure schema matches code

```bash
DATABASE_URL_SYNC=postgresql+psycopg://...clinic_restored \
  uv run --directory apps/api alembic upgrade head
```

## 5. Smoke test

```bash
psql ... -c "SELECT count(*) FROM patients;"
psql ... -c "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 5;"
```

Run the API against the restored DB locally and walk through the happy paths
(login, list patients, render a prescription PDF).

## 6. Promote (only if you intend to replace prod)

1. Set the prod app to maintenance mode (Fly: `flyctl scale count 0` for API,
   put `web` behind a banner).
2. Re-run the export against the *live* DB one more time to catch deltas.
3. Repeat step 3 above against the prod DB host (or rename `clinic_restored`
   to `crm`).
4. Bring the API back up; verify; clear maintenance.

> If you only need to **rescue a few rows**, restore into a side database and
> use `pg_dump --table=patients ... | psql` to copy just the rows of interest.

## What the dump does **not** contain

- The PHI encryption key (`PHI_ENCRYPTION_KEY`). Without it the encrypted
  columns are unreadable. Treat the key as your last line of defence.
- The `EXTERNAL_SHARE_HMAC_SECRET` — likewise, share-tokens issued before the
  backup remain useless without it.
