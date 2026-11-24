-- MARINA OWNER GL posting event: append-only, isolated from all existing ledgers.
-- No historical revenue, payment, inventory, supplier or proposal rows are rewritten.
CREATE TABLE owner_accounting_postings (
  id uuid PRIMARY KEY,
  "propertyId" uuid NOT NULL,
  "proposalId" uuid NOT NULL,
  "decisionId" uuid NOT NULL,
  action text NOT NULL CHECK (action IN ('POST','REVERSE')),
  "reversesId" uuid,
  "postedById" uuid NOT NULL REFERENCES staff_users(id) ON DELETE RESTRICT,
  reason text NOT NULL CHECK (char_length(trim(reason)) BETWEEN 8 AND 500),
  "accountingDate" date NOT NULL,
  "policyVersion" text NOT NULL,
  "createdAt" timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT marina_posting_proposal_tenant_fk FOREIGN KEY ("propertyId","proposalId")
    REFERENCES owner_accounting_journal_proposals ("propertyId",id) ON DELETE RESTRICT,
  CONSTRAINT marina_posting_decision_fk FOREIGN KEY ("decisionId")
    REFERENCES owner_accounting_journal_decisions(id) ON DELETE RESTRICT,
  CONSTRAINT marina_posting_reversal_fk FOREIGN KEY ("reversesId")
    REFERENCES owner_accounting_postings(id) ON DELETE RESTRICT,
  CONSTRAINT marina_posting_action_shape CHECK (
    (action='POST' AND "reversesId" IS NULL) OR
    (action='REVERSE' AND "reversesId" IS NOT NULL)
  ),
  CONSTRAINT marina_posting_once_per_proposal UNIQUE ("propertyId","proposalId",action),
  CONSTRAINT marina_posting_property_id_unique UNIQUE ("propertyId",id)
);

CREATE TABLE owner_accounting_posting_lines (
  "postingId" uuid NOT NULL,
  "propertyId" uuid NOT NULL,
  "lineNo" integer NOT NULL CHECK ("lineNo" BETWEEN 1 AND 128),
  "accountCode" text NOT NULL CHECK ("accountCode" IN
    ('1100','1200','2100','4000','4100','5000','6000')),
  side text NOT NULL CHECK (side IN ('DEBIT','CREDIT')),
  "amountKgs" numeric(20,4) NOT NULL CHECK ("amountKgs">0),
  memo text NOT NULL DEFAULT '',
  PRIMARY KEY ("postingId","lineNo"),
  CONSTRAINT marina_posting_lines_tenant_fk FOREIGN KEY ("propertyId","postingId")
    REFERENCES owner_accounting_postings("propertyId",id) ON DELETE RESTRICT
);
CREATE INDEX marina_posting_period_idx
  ON owner_accounting_postings("propertyId","accountingDate", "createdAt");

CREATE TRIGGER marina_posting_no_mutation
  BEFORE UPDATE OR DELETE ON owner_accounting_postings
  FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();
CREATE TRIGGER marina_posting_line_no_mutation
  BEFORE UPDATE OR DELETE ON owner_accounting_posting_lines
  FOR EACH ROW EXECUTE FUNCTION reject_owner_accounting_journal_mutation();

-- Only genuine independent approved proposals are eligible; no API bypass or
-- one-hotel-to-another posting through direct SQL.
CREATE FUNCTION marina_validate_owner_posting() RETURNS trigger AS $$
DECLARE
  proposal record;
  reviewer record;
  poster record;
  original record;
  source_ok boolean;
  source_amount numeric(20,4);
  source_kind text;
  valid_revenue_line_count integer;
  corrections_exist boolean;
  debit_total numeric(20,4);
  credit_total numeric(20,4);
  line_count integer;
  difference_count integer;
BEGIN
  IF TG_TABLE_NAME = 'owner_accounting_posting_lines' THEN
    IF (SELECT xmin::text::bigint FROM owner_accounting_postings
        WHERE id=NEW."postingId" AND "propertyId"=NEW."propertyId")
       IS DISTINCT FROM (txid_current() % 4294967296) THEN
       RAISE EXCEPTION 'ACCOUNTING_POSTING_LINES_SEALED' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
  END IF;

  IF TG_WHEN = 'BEFORE' THEN
    SELECT * INTO proposal FROM owner_accounting_journal_proposals
      WHERE id=NEW."proposalId" AND "propertyId"=NEW."propertyId";
    SELECT * INTO reviewer FROM owner_accounting_journal_decisions
      WHERE id=NEW."decisionId" AND "propertyId"=NEW."propertyId"
        AND "proposalId"=NEW."proposalId" AND action='APPROVE';
    SELECT "propertyId",role::text AS role,"isActive" AS active INTO poster
      FROM staff_users WHERE id=NEW."postedById";
    IF proposal.id IS NULL OR reviewer.id IS NULL
       OR poster."propertyId" IS DISTINCT FROM NEW."propertyId"
       OR poster.role IS DISTINCT FROM 'OWNER' OR poster.active IS DISTINCT FROM true
       OR NEW."postedById" IN (proposal."createdById", reviewer."actorId")
       OR NEW."accountingDate" IS DISTINCT FROM proposal."accountingDate"
       OR NEW."policyVersion" IS DISTINCT FROM proposal."policyVersion" THEN
       RAISE EXCEPTION 'ACCOUNTING_POSTING_UNAUTHORIZED_OR_UNMATCHED'
         USING ERRCODE='23514';
    END IF;
    IF NEW.action='POST' THEN
      IF EXISTS (SELECT 1 FROM owner_accounting_journal_decisions d
        WHERE d."propertyId"=NEW."propertyId" AND d."proposalId"=NEW."proposalId"
          AND d.action='REVERSE') THEN
        RAISE EXCEPTION 'ACCOUNTING_APPROVAL_REVERSED' USING ERRCODE='23514';
      END IF;
      IF proposal."sourceType"='REVENUE_SOURCE' THEN
        SELECT s."faceValueKgs",s."sourceType" INTO source_amount,source_kind
          FROM owner_revenue_source_events s
         WHERE s.id=proposal."sourceId" AND s."propertyId"=NEW."propertyId"
           AND s.action='APPROVE_SOURCE';
        SELECT EXISTS (SELECT 1 FROM owner_revenue_source_events s
          WHERE s.id=proposal."sourceId" AND s."propertyId"=NEW."propertyId"
            AND s.action='APPROVE_SOURCE'
            AND NOT EXISTS (SELECT 1 FROM owner_revenue_source_events r
              WHERE r."propertyId"=NEW."propertyId" AND r."reversesId"=s.id)
        ) INTO source_ok;
        -- Corrections, taxes and packages require separate reviewed posting
        -- policy; never silently post the unadjusted face amount.
        SELECT EXISTS (SELECT 1 FROM owner_revenue_correction_events c
          WHERE c."propertyId"=NEW."propertyId"
            AND c."approvalId"=proposal."sourceId" AND c.action='RECORD'
            AND NOT EXISTS(SELECT 1 FROM owner_revenue_correction_events r
              WHERE r."propertyId"=NEW."propertyId" AND r."reversesId"=c.id))
          INTO corrections_exist;
        IF source_ok IS DISTINCT FROM true OR corrections_exist IS TRUE THEN
          RAISE EXCEPTION 'ACCOUNTING_REVENUE_SOURCE_UNRECONCILED'
            USING ERRCODE='23514';
        END IF;
        -- No arbitrary proposal amount / manual chart may become revenue.
        -- Only exactly one receivable and one matching source-type revenue.
        SELECT COUNT(*) INTO valid_revenue_line_count
        FROM owner_accounting_journal_proposal_lines l
        WHERE l."proposalId"=proposal.id
          AND l."amountKgs"=source_amount
          AND ((l."accountCode"='1100' AND l.side='DEBIT')
            OR (l."accountCode"=CASE source_kind
                 WHEN 'ROOM_NIGHT' THEN '4000'
                 WHEN 'DINING_ORDER' THEN '4100' ELSE '~INVALID~' END
                AND l.side='CREDIT'));
        IF source_amount<=0 OR valid_revenue_line_count<>2
           OR (SELECT COUNT(*) FROM owner_accounting_journal_proposal_lines
               WHERE "proposalId"=proposal.id)<>2 THEN
          RAISE EXCEPTION 'ACCOUNTING_REVENUE_ACCOUNT_OR_AMOUNT_INVALID'
            USING ERRCODE='23514';
        END IF;
      ELSE
        -- Until explicit mapping exists for correction/COGS/tax expenses,
        -- these proposal types stay read-only and cannot be posted.
        RAISE EXCEPTION 'ACCOUNTING_POSTING_POLICY_NOT_RELEASED'
          USING ERRCODE='23514';
      END IF;
    ELSE
      SELECT * INTO original FROM owner_accounting_postings
        WHERE id=NEW."reversesId" AND "propertyId"=NEW."propertyId"
          AND "proposalId"=NEW."proposalId" AND action='POST';
      IF original.id IS NULL OR original."decisionId"<>NEW."decisionId" THEN
        RAISE EXCEPTION 'ACCOUNTING_REVERSAL_TARGET_INVALID'
          USING ERRCODE='23514';
      END IF;
    END IF;
    RETURN NEW;
  END IF;
  -- Deferred exact line matching and balanced sums: no partial or arbitrary GL.
  SELECT COUNT(*)::integer,
         COALESCE(SUM("amountKgs") FILTER (WHERE side='DEBIT'),0),
         COALESCE(SUM("amountKgs") FILTER (WHERE side='CREDIT'),0)
    INTO line_count,debit_total,credit_total
    FROM owner_accounting_posting_lines WHERE "postingId"=NEW.id;
  IF line_count<2 OR debit_total<=0 OR debit_total<>credit_total THEN
    RAISE EXCEPTION 'ACCOUNTING_POSTING_UNBALANCED' USING ERRCODE='23514';
  END IF;
  IF NEW.action='POST' THEN
    SELECT COUNT(*)::integer INTO difference_count FROM (
      (SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW.id
       EXCEPT
       SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_journal_proposal_lines
         WHERE "proposalId"=NEW."proposalId")
      UNION ALL
      (SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=NEW."proposalId"
       EXCEPT
       SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW.id)
    ) delta;
  ELSE
    SELECT COUNT(*)::integer INTO difference_count FROM (
      (SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW.id
       EXCEPT
       SELECT "lineNo","accountCode",
              CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END AS side,
              "amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW."reversesId")
      UNION ALL
      (SELECT "lineNo","accountCode",
              CASE side WHEN 'DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END AS side,
              "amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW."reversesId"
       EXCEPT
       SELECT "lineNo","accountCode",side,"amountKgs",memo
         FROM owner_accounting_posting_lines WHERE "postingId"=NEW.id)
    ) delta;
  END IF;
  IF difference_count>0 THEN
    RAISE EXCEPTION 'ACCOUNTING_POSTING_LINES_DIFFER_FROM_APPROVED'
      USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER marina_posting_before_insert
  BEFORE INSERT ON owner_accounting_postings
  FOR EACH ROW EXECUTE FUNCTION marina_validate_owner_posting();
CREATE TRIGGER marina_posting_line_before_insert
  BEFORE INSERT ON owner_accounting_posting_lines
  FOR EACH ROW EXECUTE FUNCTION marina_validate_owner_posting();
CREATE CONSTRAINT TRIGGER marina_posting_deferred_check
  AFTER INSERT ON owner_accounting_postings
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION marina_validate_owner_posting();

-- 54th migration is intentionally a *staged* journal primitive, not proof of
-- complete P&L; no revenue, cash, tax, cost or inventory is auto-reclassified.
