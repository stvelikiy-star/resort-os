-- FLEX preview 0005: independent PMS deployment key and one-time linkage challenge.
-- Apply ONLY to a disposable FLEX QA PostgreSQL after preview 0001-0004.
-- Trusted deployment keys are pre-enrolled by a separate audited security process;
-- there is deliberately NO network endpoint to self-register as a deployment.
BEGIN;

CREATE TABLE flex_trusted_deployments (
  deployment_id text PRIMARY KEY
    CHECK (deployment_id ~ '^[A-Za-z0-9][A-Za-z0-9_.-]{3,99}$'),
  public_key_pem text NOT NULL CHECK (length(public_key_pem) BETWEEN 70 AND 2000),
  key_fingerprint_sha256 char(64) NOT NULL UNIQUE
    CHECK (key_fingerprint_sha256 ~ '^[a-f0-9]{64}$'),
  state text NOT NULL DEFAULT 'TRUSTED' CHECK (state IN ('TRUSTED','REVOKED')),
  enrolled_at timestamptz NOT NULL DEFAULT now(),
  enrolled_by text NOT NULL
);
ALTER TABLE flex_trusted_deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_trusted_deployments FORCE ROW LEVEL SECURITY;

CREATE TABLE flex_hotel_link_challenges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  deployment_id text NOT NULL REFERENCES flex_trusted_deployments(deployment_id),
  property_external_id text NOT NULL
    CHECK (length(property_external_id) BETWEEN 1 AND 180),
  nonce text NOT NULL UNIQUE CHECK (length(nonce) BETWEEN 32 AND 160),
  signed_message text NOT NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL REFERENCES flex_platform_memberships(subject_id),
  consumed_at timestamptz,
  CHECK (expires_at > created_at),
  UNIQUE (id,hotel_id)
);
ALTER TABLE flex_hotel_link_challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_hotel_link_challenges FORCE ROW LEVEL SECURITY;

GRANT SELECT ON flex_trusted_deployments TO flex_onboarding_writer;
GRANT SELECT,INSERT,UPDATE(consumed_at) ON flex_hotel_link_challenges TO flex_onboarding_writer;
GRANT INSERT ON flex_hotel_links TO flex_onboarding_writer;
ALTER TABLE flex_hotel_links FORCE ROW LEVEL SECURITY;

CREATE POLICY flex_writer_trusted_deployments ON flex_trusted_deployments
FOR SELECT TO flex_onboarding_writer USING (state='TRUSTED');

CREATE POLICY flex_writer_link_challenge_read ON flex_hotel_link_challenges
FOR SELECT TO flex_onboarding_writer
USING (created_by = NULLIF(current_setting('flex.actor_subject_id',true),''));

CREATE POLICY flex_writer_link_challenge_insert ON flex_hotel_link_challenges
FOR INSERT TO flex_onboarding_writer
WITH CHECK (
  created_by = NULLIF(current_setting('flex.actor_subject_id',true),'')
  AND consumed_at IS NULL
  AND expires_at <= created_at + interval '15 minutes'
);

CREATE POLICY flex_writer_link_challenge_consume ON flex_hotel_link_challenges
FOR UPDATE TO flex_onboarding_writer
USING (
  created_by = NULLIF(current_setting('flex.actor_subject_id',true),'')
  AND consumed_at IS NULL
)
WITH CHECK (
  created_by = NULLIF(current_setting('flex.actor_subject_id',true),'')
  AND consumed_at IS NOT NULL
);

CREATE POLICY flex_writer_verified_link_insert ON flex_hotel_links
FOR INSERT TO flex_onboarding_writer
WITH CHECK (verified_at IS NOT NULL);

CREATE POLICY flex_writer_link_audit_insert ON flex_audit_events
FOR INSERT TO flex_onboarding_writer
WITH CHECK (
  platform_subject_id = NULLIF(current_setting('flex.actor_subject_id',true),'')
  AND action='HOTEL_PMS_LINK_VERIFIED'
  AND resource_type='FLEX_HOTEL'
);

CREATE INDEX flex_link_challenges_hotel ON flex_hotel_link_challenges(hotel_id,expires_at);
COMMENT ON TABLE flex_trusted_deployments IS
  'Out-of-band approved public signing keys of MARINA PMS deployments; no self-enrolment';
COMMENT ON TABLE flex_hotel_link_challenges IS
  'Single-use signed PMS attestation before commercial hotel can be linked';

COMMIT;
