-- Postgres extensions required by clinic-crm.
-- Loaded on first boot of the Postgres container via /docker-entrypoint-initdb.d.

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- pgp_sym_encrypt for PHI columns
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive email/slug
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- patient search (trigram)
