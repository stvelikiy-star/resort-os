-- Immutable, property-scoped primary-document bytes for OWNER finance.
-- Bounded BYTEA is intentionally self-contained in PostgreSQL: backup/restore
-- captures document and correction atomically without a new external host.
-- Hash is independently computed by the API from the stored input bytes.
CREATE TABLE owner_revenue_evidence_documents (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
  "documentReference" text NOT NULL,
  "documentDate" date NOT NULL,
  "fileName" text NOT NULL,
  "mediaType" text NOT NULL,
  "sha256" text NOT NULL,
  "content" bytea NOT NULL,
  "sizeBytes" integer NOT NULL,
  "uploadedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT owner_revenue_evidence_reference_check CHECK
    (char_length("documentReference") BETWEEN 4 AND 150),
  CONSTRAINT owner_revenue_evidence_filename_check CHECK
    (char_length("fileName") BETWEEN 1 AND 128),
  CONSTRAINT owner_revenue_evidence_mime_check CHECK
    ("mediaType" IN ('application/pdf','image/png','image/jpeg')),
  CONSTRAINT owner_revenue_evidence_sha_check CHECK
    ("sha256" ~ '^[0-9a-f]{64}$'),
  CONSTRAINT owner_revenue_evidence_size_check CHECK
    ("sizeBytes" BETWEEN 1 AND 2097152 AND
     octet_length("content")="sizeBytes"),
  CONSTRAINT owner_revenue_evidence_property_id_unique
    UNIQUE ("propertyId",id)
);

CREATE INDEX owner_revenue_evidence_period_idx
 ON owner_revenue_evidence_documents
 ("propertyId","documentDate","createdAt" DESC);

ALTER TABLE owner_revenue_correction_events
 ADD COLUMN "evidenceDocumentId" uuid;
ALTER TABLE owner_revenue_correction_events
 ADD CONSTRAINT owner_revenue_correction_document_property_fkey
 FOREIGN KEY ("propertyId","evidenceDocumentId")
 REFERENCES owner_revenue_evidence_documents ("propertyId",id)
 ON DELETE RESTRICT;

-- Newly recorded corrections MUST have a verified byte-backed document.
-- The constraint is NOT VALID to retain legacy historical metadata-only rows
-- if the prior Draft schema was already used on an isolated test database.
ALTER TABLE owner_revenue_correction_events
 ADD CONSTRAINT owner_revenue_correction_new_document_check
 CHECK (action <> 'RECORD' OR "evidenceDocumentId" IS NOT NULL)
 NOT VALID;

CREATE FUNCTION reject_owner_revenue_evidence_mutation() RETURNS trigger AS $$
BEGIN
 RAISE EXCEPTION 'OWNER_REVENUE_EVIDENCE_IMMUTABLE';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER owner_revenue_evidence_append_only
 BEFORE UPDATE OR DELETE ON owner_revenue_evidence_documents
 FOR EACH ROW EXECUTE FUNCTION reject_owner_revenue_evidence_mutation();
