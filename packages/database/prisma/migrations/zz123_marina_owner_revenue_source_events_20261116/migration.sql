-- P0: immutable evidence that OWNER approved one delivered source, NOT revenue P&L.
-- An approval may be reversed by appending a separate event, never overwritten.
-- Source fact types are intentionally restricted to inspected, source-qualified
-- room-night and served-order/folio flows. No customer Payment is generated.
CREATE TABLE owner_revenue_source_events (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
  "sourceType" text NOT NULL,
  "sourceId" uuid NOT NULL,
  "serviceDate" date NOT NULL,
  action text NOT NULL,
  "faceValueKgs" numeric(20,4) NOT NULL,
  "sourceSnapshot" jsonb NOT NULL,
  "reversesId" uuid,
  reason text NOT NULL,
  "createdById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT owner_revenue_source_action_check
    CHECK (action IN ('APPROVE_SOURCE','REVERSE_SOURCE')),
  CONSTRAINT owner_revenue_source_type_check
    CHECK ("sourceType" IN ('ROOM_NIGHT','DINING_ORDER')),
  CONSTRAINT owner_revenue_source_amount_check
    CHECK ("faceValueKgs" >= 0),
  CONSTRAINT owner_revenue_source_reason_check
    CHECK (char_length(reason) BETWEEN 8 AND 500),
  CONSTRAINT owner_revenue_source_snapshot_check
    CHECK (jsonb_typeof("sourceSnapshot")='object'),
  CONSTRAINT owner_revenue_source_reversal_shape_check
    CHECK ((action='APPROVE_SOURCE' AND "reversesId" IS NULL)
        OR (action='REVERSE_SOURCE' AND "reversesId" IS NOT NULL)),
  CONSTRAINT owner_revenue_source_property_event_unique
    UNIQUE ("propertyId",id),
  CONSTRAINT owner_revenue_source_reversal_property_fkey
    FOREIGN KEY ("propertyId","reversesId")
    REFERENCES owner_revenue_source_events("propertyId",id) ON DELETE RESTRICT
);
-- One source/date may have exactly one original approval event, even after
-- reversal. Corrective changes must append an explicit accounting adjustment
-- in a later approved policy, not silently replace source evidence.
CREATE UNIQUE INDEX owner_revenue_source_one_approval
  ON owner_revenue_source_events ("propertyId","sourceType","sourceId","serviceDate")
  WHERE action='APPROVE_SOURCE';
CREATE UNIQUE INDEX owner_revenue_source_one_reversal
  ON owner_revenue_source_events ("reversesId")
  WHERE action='REVERSE_SOURCE';
CREATE INDEX owner_revenue_source_property_period_idx
  ON owner_revenue_source_events ("propertyId","serviceDate","createdAt" DESC);

-- Protect history from mutations made outside the API as well as inside it.
CREATE FUNCTION reject_owner_revenue_source_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'OWNER_REVENUE_SOURCE_IMMUTABLE';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER owner_revenue_source_append_only
  BEFORE UPDATE OR DELETE ON owner_revenue_source_events
  FOR EACH ROW EXECUTE FUNCTION reject_owner_revenue_source_mutation();
