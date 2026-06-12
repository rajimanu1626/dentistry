# Rotate PHI encryption + share HMAC keys

## PHI_ENCRYPTION_KEY

Encrypts patient PHI columns via `pgp_sym_encrypt`.

### 1. Generate a new key

```bash
openssl rand -base64 32   # store as PHI_ENCRYPTION_KEY_NEW in your secrets store
```

### 2. Re-encrypt every row

Write a one-off Alembic data migration:

```python
def upgrade():
    old = os.environ["PHI_ENCRYPTION_KEY"]
    new = os.environ["PHI_ENCRYPTION_KEY_NEW"]
    for col in ("phone_enc", "address_enc", "allergies_enc", "medical_history_enc"):
        op.execute(
            f"""
            UPDATE patients
            SET {col} = pgp_sym_encrypt(pgp_sym_decrypt({col}, '{old}'), '{new}')
            WHERE {col} IS NOT NULL;
            """
        )
```

Run it with `PHI_ENCRYPTION_KEY=<old> PHI_ENCRYPTION_KEY_NEW=<new> alembic upgrade head`.
Then swap the secret in Fly / GitHub.

## EXTERNAL_SHARE_HMAC_SECRET

Rotating this secret **invalidates every outstanding external share link** —
which is exactly what you want during a suspected leak.

```bash
openssl rand -base64 32
flyctl secrets set EXTERNAL_SHARE_HMAC_SECRET=<new-value>
# Optionally bulk-revoke old links so /share/<token> returns 410 instantly:
psql "$DATABASE_URL_SYNC" -c "UPDATE external_share_links SET revoked_at = now() WHERE revoked_at IS NULL;"
```

## JWT_SIGNING_KEY (local IDENTITY_PROVIDER only)

```bash
openssl rand -base64 32
flyctl secrets set JWT_SIGNING_KEY=<new-value>
```

All issued tokens become invalid immediately; users must re-login.
