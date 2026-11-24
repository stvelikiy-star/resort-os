-- MARINA FLEX isolated CI preflight. Run BEFORE any preview migration.
-- This file intentionally allows ONLY the two literal ephemeral GitHub Actions
-- PostgreSQL DB names. It must NEVER be reused as a Supabase production recipe.
DO $preflight$
DECLARE
  existing int;
BEGIN
  IF current_database() <> 'flex_ci' THEN
    RAISE EXCEPTION 'FLEX_QA_ONLY_DATABASE_REQUIRED: %', current_database();
  END IF;
  IF current_setting('server_version_num')::int < 160000
     OR current_setting('server_version_num')::int >= 170000 THEN
    RAISE EXCEPTION 'FLEX_QA_REQUIRES_POSTGRESQL_16';
  END IF;
  -- Never run these preview objects on a Supabase database or PMS with
  -- user objects. Supabase systems are deliberately not qualified QA here.
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname IN
    ('auth','storage','realtime','supabase_functions'))
     OR EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN
       ('anon','authenticated','service_role'))
  THEN
    RAISE EXCEPTION 'FLEX_QA_MUST_NOT_BE_SUPABASE_OR_PMS';
  END IF;
  SELECT count(*) INTO existing
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f');
  IF existing<>0 THEN
    RAISE EXCEPTION 'FLEX_QA_DATABASE_NOT_EMPTY: % objects', existing;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
             WHERE n.nspname='public' AND p.proname NOT LIKE 'gen_random_uuid')
  THEN
    RAISE EXCEPTION 'FLEX_QA_UNEXPECTED_PUBLIC_FUNCTIONS';
  END IF;
END
$preflight$;
SELECT current_database() AS confirmed_ephemeral_flex_ci;
