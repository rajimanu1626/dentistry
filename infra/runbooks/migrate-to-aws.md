# Migrate Supabase → AWS RDS + Cognito + S3 + ECS

This runbook stays in sync with the env-var contract via the
`scripts/check_portability.py` invariants and the workflow in `.github/workflows/pr.yml`.

> Expected duration end-to-end: ~4–6 hours including a 24-hour soak with
> Supabase kept read-only as a rollback.

## 0. Preconditions

- [ ] All eight **Portability invariants** in `CLAUDE.md` are still satisfied
      (`python3 scripts/check_portability.py` is green).
- [ ] Latest backup has been restored to a *throwaway* RDS instance successfully
      (`infra/runbooks/restore-db.md`).
- [ ] `terraform plan` against `infra/aws/` is clean.

## 1. Provision the AWS estate

```bash
cd infra/aws
terraform init
terraform apply -var "api_image=ghcr.io/<org>/clinic-crm-api:sha-<tag>" \
                -var "db_password=<rand>" \
                -var-file=prod.tfvars
```

This creates: VPC + private subnets, RDS Postgres 16 (with `pgcrypto`,
`pgaudit`), Cognito user pool (with MFA), S3 media bucket, ECS Fargate cluster,
CloudWatch log group.

## 2. Database setup

```bash
psql "$DATABASE_URL_SYNC" \
  -f apps/api/../../infra/db/init/00-extensions.sql \
  -f apps/api/../../infra/db/init/10-roles.sql

DATABASE_URL_SYNC=... uv run --directory apps/api alembic upgrade head
```

## 3. Data migration

```bash
pg_dump "$SUPABASE_URL" \
  --format=custom --no-owner --no-acl \
  --exclude-schema=auth --exclude-schema=storage --exclude-schema=realtime \
  > dump.pgcustom

pg_restore -d "$RDS_URL" --no-owner --no-acl --jobs=4 dump.pgcustom
```

## 4. User identity migration

```bash
# scripts/migrate_users_to_cognito.py (already in repo) — iterates our users
# table, creates Cognito users, emails a password reset to each.
uv run --directory apps/api python -m scripts.migrate_users_to_cognito \
  --cognito-pool-id "$(terraform output -raw cognito_user_pool_id)"
```

> The script never touches `auth.users` (Supabase) — we always owned a local
> `users` table per portability invariant #2.

## 5. Object storage migration

```bash
aws s3 sync \
  s3://<supabase-bucket>/  \
  s3://$(terraform output -raw media_bucket_name)/ \
  --source-region <supabase-region> --region "$AWS_REGION"
```

Switch the API env:

```diff
- S3_ENDPOINT=https://<project>.supabase.co/storage/v1/s3
+ S3_ENDPOINT=https://s3.ap-south-1.amazonaws.com
- S3_BUCKET=clinic-crm-prod
+ S3_BUCKET=clinic-crm-prod-media
- S3_FORCE_PATH_STYLE=true
+ S3_FORCE_PATH_STYLE=false
```

No application code changes — same boto3 calls.

## 6. Identity provider env switch

```diff
- IDENTITY_PROVIDER=supabase
- JWKS_URL=https://<project>.supabase.co/auth/v1/keys
+ IDENTITY_PROVIDER=cognito
+ JWKS_URL=https://cognito-idp.ap-south-1.amazonaws.com/<pool-id>/.well-known/jwks.json
+ JWT_AUDIENCE=<cognito-client-id>
+ JWT_ISSUER=https://cognito-idp.ap-south-1.amazonaws.com/<pool-id>
```

Place all secrets into AWS Secrets Manager and wire them into the ECS task as
`secrets` entries (one per env var) — see `infra/aws/ecs.tf` `secrets = []` slot.

## 7. Cut DNS

```bash
# Lower the TTL 24h in advance to 60s.
# Then flip the AAAA/A record from Fly to the ALB / CloudFront target.
```

## 8. Verification

- [ ] `/healthz`, `/readyz` are 200
- [ ] `bun run test:e2e` against production passes with a synthetic clinic
- [ ] Audit log records the cutover
- [ ] PHI decryption works (open a patient, see decrypted phone)
- [ ] An external share link issued before the cutover **does not** work (good
      if you rotated `EXTERNAL_SHARE_HMAC_SECRET` per `rotate-keys.md`; otherwise
      old links remain valid — that's the intended trade-off).

## 9. Soak + rollback window

- Keep Supabase in **read-only** for 24 hours.
- DNS TTL still low: a single env-var flip (`DATABASE_URL`, `S3_ENDPOINT`,
  `JWKS_URL`) reverts the whole stack to Supabase without code changes.

## 10. Cleanup

- After 24h soak, raise the DNS TTL back to its normal value.
- Cancel the Supabase project (export billing receipt for the books).
- Remove the rollback DNS record.
