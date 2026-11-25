-- FLEX preview 0004: safe PENDING commercial-hotel onboarding.
-- Only after 0001/0002/0003 in an isolated disposable FLEX DB.
-- Does not connect to a PMS property or activate any subscription.
BEGIN;

CREATE TABLE flex_hotel_onboarding_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_subject_id text NOT NULL REFERENCES flex_platform_memberships(subject_id),
  idempotency_key text NOT NULL,
  payload_sha256 char(64) NOT NULL CHECK (payload_sha256 ~ '^[a-f0-9]{64}$'),
  hotel_id uuid NOT NULL UNIQUE REFERENCES flex_hotels(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (actor_subject_id,idempotency_key)
);
ALTER TABLE flex_hotel_onboarding_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_hotel_onboarding_requests FORCE ROW LEVEL SECURITY;

-- This role must be granted with INHERIT FALSE to a dedicated runtime DB login.
-- The runtime may SET LOCAL ROLE only after signed JWT + database membership + MFA.
CREATE ROLE flex_onboarding_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO flex_onboarding_writer;
GRANT SELECT,INSERT ON flex_hotels,flex_hotel_onboarding_requests TO flex_onboarding_writer;
GRANT INSERT ON flex_audit_events TO flex_onboarding_writer;

-- Only a new PENDING client can be created. No UPDATE or DELETE permissions.
CREATE POLICY flex_onboarding_hotel_insert ON flex_hotels
FOR INSERT TO flex_onboarding_writer
WITH CHECK (status='PENDING' AND billing_currency='KGS');
CREATE POLICY flex_onboarding_hotel_select ON flex_hotels
FOR SELECT TO flex_onboarding_writer
USING (status='PENDING');

CREATE POLICY flex_onboarding_request_insert ON flex_hotel_onboarding_requests
FOR INSERT TO flex_onboarding_writer
WITH CHECK (
  actor_subject_id = NULLIF(current_setting('flex.actor_subject_id',true),'')
);
CREATE POLICY flex_onboarding_request_select ON flex_hotel_onboarding_requests
FOR SELECT TO flex_onboarding_writer
USING (
  actor_subject_id = NULLIF(current_setting('flex.actor_subject_id',true),'')
);

CREATE POLICY flex_onboarding_audit_insert ON flex_audit_events
FOR INSERT TO flex_onboarding_writer
WITH CHECK (
  platform_subject_id = NULLIF(current_setting('flex.actor_subject_id',true),'')
  AND action='HOTEL_REGISTERED'
  AND resource_type='FLEX_HOTEL'
);
ALTER TABLE flex_audit_events FORCE ROW LEVEL SECURITY;

COMMENT ON TABLE flex_hotel_onboarding_requests IS
  'Idempotent commercial registration only; no trusted PMS deployment link until attestation';
COMMENT ON ROLE flex_onboarding_writer IS
  'No-login append-only PENDING hotel writer, trusted API only, no PMS access';

COMMIT;
