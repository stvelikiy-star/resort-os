-- Append-only OWNER correction *evidence*, not recognized revenue or a Payment.
-- Every correction is attached to an already approved delivered-source event;
-- a supplied document fingerprint is a manual reference, NOT proof of document
-- content until independently verified and accepted by accounting.
CREATE TABLE owner_revenue_correction_events (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
  "approvalId" uuid NOT NULL,
  action text NOT NULL,
  kind text NOT NULL,
  component text NOT NULL,
  "amountKgs" numeric(20,4) NOT NULL,
  "documentReference" text NOT NULL,
  "documentDate" date NOT NULL,
  "documentSha256" text NOT NULL,
  "evidenceReference" text NOT NULL,
  reason text NOT NULL,
  "reversesId" uuid,
  "sourceSnapshot" jsonb NOT NULL,
  "createdById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT owner_revenue_correction_action_check CHECK
    (action IN ('RECORD','REVERSE')),
  CONSTRAINT owner_revenue_correction_kind_check CHECK
    (kind IN ('DISCOUNT','PACKAGE_SPLIT','CANCELLATION','REFUND','TAX_COMPONENT')),
  CONSTRAINT owner_revenue_correction_component_check CHECK
    (component IN ('LODGING','DINING','OTHER','UNALLOCATED')),
  CONSTRAINT owner_revenue_correction_amount_check CHECK
    ("amountKgs">0),
  CONSTRAINT owner_revenue_correction_reference_check CHECK
    (char_length("documentReference") BETWEEN 4 AND 150 AND
     char_length("evidenceReference") BETWEEN 8 AND 300 AND
     char_length(reason) BETWEEN 8 AND 500),
  CONSTRAINT owner_revenue_correction_sha_check CHECK
    ("documentSha256" ~ '^[0-9a-f]{64}$'),
  CONSTRAINT owner_revenue_correction_snapshot_check CHECK
    (jsonb_typeof("sourceSnapshot")='object'),
  CONSTRAINT owner_revenue_correction_reversal_shape_check CHECK
    ((action='RECORD' AND "reversesId" IS NULL) OR
     (action='REVERSE' AND "reversesId" IS NOT NULL)),
  CONSTRAINT owner_revenue_correction_approval_property_fkey
    FOREIGN KEY ("propertyId","approvalId")
    REFERENCES owner_revenue_source_events("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT owner_revenue_correction_id_property_unique UNIQUE ("propertyId",id),
  CONSTRAINT owner_revenue_correction_reversed_property_fkey
    FOREIGN KEY ("propertyId","reversesId")
    REFERENCES owner_revenue_correction_events("propertyId",id) ON DELETE RESTRICT
);

-- A repeat of a source+document+kind+component must not generate another
-- monetary correction, even with a new client event ID.
CREATE UNIQUE INDEX owner_revenue_correction_document_once
 ON owner_revenue_correction_events
 ("propertyId","approvalId",kind,component,"documentReference")
 WHERE action='RECORD';
CREATE UNIQUE INDEX owner_revenue_correction_reversal_once
 ON owner_revenue_correction_events ("reversesId")
 WHERE action='REVERSE';
CREATE INDEX owner_revenue_correction_period
 ON owner_revenue_correction_events ("propertyId","documentDate","createdAt" DESC);

CREATE FUNCTION reject_owner_revenue_correction_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'OWNER_REVENUE_CORRECTION_IMMUTABLE';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_revenue_correction_append_only
 BEFORE UPDATE OR DELETE ON owner_revenue_correction_events
 FOR EACH ROW EXECUTE FUNCTION reject_owner_revenue_correction_mutation();
