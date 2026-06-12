-- Application + external-share DB roles.
-- The app and the external-share endpoints connect as *non-superuser* roles so
-- RLS cannot be bypassed.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user LOGIN PASSWORD 'app_user';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'share_reader') THEN
    -- minimal-privilege role used only by /share/* endpoints (phase 7).
    CREATE ROLE share_reader LOGIN PASSWORD 'share_reader';
  END IF;
END $$;

-- The session-variable that RLS policies key off. Whitelist here so callers can
-- only set the variables we expect, never arbitrary ones.
ALTER DATABASE crm SET app.current_user_id = '00000000-0000-0000-0000-000000000000';
ALTER DATABASE crm SET app.current_clinic_id = '00000000-0000-0000-0000-000000000000';

GRANT CONNECT ON DATABASE crm TO app_user, share_reader;
GRANT USAGE ON SCHEMA public TO app_user, share_reader;
