-- MARINA FLEX 0010 — synthetic partner earnings and protected statements.
-- PREVIEW ONLY. Applies after 0001–0009 to a disposable central PostgreSQL.
-- Existing accommodation, KÖL, and production databases are out of scope.
-- No real payouts. Every event below is marked QA_ONLY.
BEGIN;

ALTER TABLE flex_investor_contract_versions ADD CONSTRAINT flex_investor_contract_owner_fk
  UNIQUE(id, investor_id);

CREATE TABLE flex_partner_rule_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hotel_id uuid NOT NULL REFERENCES flex_hotels(id),
  sku text NOT NULL REFERENCES flex_skus(sku),
  agent_id uuid REFERENCES flex_agents(id),
  investor_id uuid REFERENCES flex_investors(id),
  investor_contract_version_id uuid,
  version integer NOT NULL CHECK(version > 0),
  rate_bps integer NOT NULL CHECK(rate_bps BETWEEN 0 AND 10000),
  eligible_basis text NOT NULL DEFAULT 'TAX_EXCLUDED_CASH'
    CHECK(eligible_basis='TAX_EXCLUDED_CASH'),
  approved_by text NOT NULL,
  approval_digest char(64) NOT NULL CHECK(approval_digest ~ '^[0-9a-f]{64}$'),
  effective_from timestamptz NOT NULL,
  effective_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK ( (agent_id IS NOT NULL AND investor_id IS NULL AND
            investor_contract_version_id IS NULL)
       OR (agent_id IS NULL AND investor_id IS NOT NULL AND
            investor_contract_version_id IS NOT NULL) ),
  CHECK(effective_until IS NULL OR effective_until>effective_from),
  FOREIGN KEY (investor_contract_version_id,investor_id)
    REFERENCES flex_investor_contract_versions(id,investor_id),
  UNIQUE(id,hotel_id,sku)
);
CREATE UNIQUE INDEX flex_agent_rule_version_scope
  ON flex_partner_rule_versions(agent_id,hotel_id,sku,version)
  WHERE agent_id IS NOT NULL;
CREATE UNIQUE INDEX flex_investor_rule_version_scope
  ON flex_partner_rule_versions(investor_contract_version_id,hotel_id,sku,version)
  WHERE investor_id IS NOT NULL;

CREATE TABLE flex_partner_earnings_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_version_id uuid NOT NULL REFERENCES flex_partner_rule_versions(id),
  agent_id uuid REFERENCES flex_agents(id),
  investor_id uuid REFERENCES flex_investors(id),
  allocation_id uuid NOT NULL REFERENCES flex_payment_allocations(id),
  source_allocation_reversal_id uuid REFERENCES flex_allocation_reversals(id),
  entry_type text NOT NULL CHECK(entry_type IN ('ACCRUAL','REVERSAL')),
  amount numeric(18,2) NOT NULL CHECK(amount>0),
  currency char(3) NOT NULL DEFAULT 'KGS' CHECK(currency='KGS'),
  provenance text NOT NULL DEFAULT 'QA_ONLY' CHECK(provenance='QA_ONLY'),
  recognized_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK((agent_id IS NOT NULL) <> (investor_id IS NOT NULL)),
  CHECK((entry_type='ACCRUAL' AND source_allocation_reversal_id IS NULL)
     OR (entry_type='REVERSAL' AND source_allocation_reversal_id IS NOT NULL))
);
CREATE UNIQUE INDEX flex_partner_once_per_allocation
 ON flex_partner_earnings_entries(rule_version_id,allocation_id)
 WHERE entry_type='ACCRUAL';
CREATE UNIQUE INDEX flex_partner_once_per_reversal
 ON flex_partner_earnings_entries(rule_version_id,source_allocation_reversal_id)
 WHERE entry_type='REVERSAL';
CREATE INDEX flex_partner_agent_statement ON flex_partner_earnings_entries(agent_id,recognized_at)
  WHERE agent_id IS NOT NULL;
CREATE INDEX flex_partner_investor_statement ON flex_partner_earnings_entries(investor_id,recognized_at)
  WHERE investor_id IS NOT NULL;

-- All rules and entries are immutable, including append-only corrections.
CREATE TRIGGER flex_partner_rule_no_rewrite
BEFORE UPDATE OR DELETE ON flex_partner_rule_versions
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();
CREATE TRIGGER flex_partner_entry_no_rewrite
BEFORE UPDATE OR DELETE ON flex_partner_earnings_entries
FOR EACH ROW EXECUTE FUNCTION flex_reject_history_rewrite();

CREATE FUNCTION flex_qa_partner_earnings_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $flex$
DECLARE
  rule_rec flex_partner_rule_versions%ROWTYPE;
  alloc_rec record;
  reversal_amount numeric(18,2);
  accrued numeric(18,2);
  reversed numeric(18,2);
  eligible_net numeric(18,2);
  allowed numeric(18,2);
BEGIN
  -- All statement entries are synthetic until a separately audited bank
  -- ledger writer is built. This cannot be used to trigger a payout.
  SELECT * INTO rule_rec FROM flex_partner_rule_versions WHERE id=NEW.rule_version_id;
  SELECT a.id, a.amount, a.payment_id, l.sku, i.hotel_id,
         t.net_amount, t.payable_amount, p.provider, p.confirmed_at
   INTO alloc_rec
   FROM flex_payment_allocations a
   JOIN flex_invoice_lines l ON l.id=a.invoice_line_id
   JOIN flex_invoices i ON i.id=l.invoice_id
   JOIN flex_issued_invoice_line_tax t ON t.invoice_line_id=l.id
   JOIN flex_confirmed_payments p ON p.id=a.payment_id
   WHERE a.id=NEW.allocation_id
   FOR UPDATE OF a;
  IF NOT FOUND OR rule_rec.id IS NULL
     OR rule_rec.hotel_id<>alloc_rec.hotel_id
     OR rule_rec.sku<>alloc_rec.sku
     OR rule_rec.agent_id IS DISTINCT FROM NEW.agent_id
     OR rule_rec.investor_id IS DISTINCT FROM NEW.investor_id
     OR alloc_rec.provider<>'FLEX_QA_SIMULATOR'
     OR alloc_rec.payable_amount<=0
     OR rule_rec.effective_from>alloc_rec.confirmed_at
     OR (rule_rec.effective_until IS NOT NULL
         AND rule_rec.effective_until<=alloc_rec.confirmed_at)
  THEN
     RAISE EXCEPTION 'FLEX_PARTNER_SCOPE_OR_SOURCE_INVALID' USING ERRCODE='23514';
  END IF;
  eligible_net := round(alloc_rec.amount * alloc_rec.net_amount /
                        alloc_rec.payable_amount,2);
  allowed := round(eligible_net * rule_rec.rate_bps::numeric / 10000,2);

  IF NEW.entry_type='ACCRUAL' THEN
    IF NEW.amount>allowed THEN
      RAISE EXCEPTION 'FLEX_PARTNER_ACCRUAL_OVER_RATE' USING ERRCODE='23514';
    END IF;
  ELSE
    SELECT ar.amount INTO reversal_amount FROM flex_allocation_reversals ar
      WHERE ar.id=NEW.source_allocation_reversal_id
        AND ar.allocation_id=NEW.allocation_id;
    IF reversal_amount IS NULL THEN
      RAISE EXCEPTION 'FLEX_PARTNER_REVERSAL_WRONG_SOURCE' USING ERRCODE='23514';
    END IF;
    SELECT coalesce(sum(e.amount),0) INTO accrued
      FROM flex_partner_earnings_entries e
      WHERE e.rule_version_id=NEW.rule_version_id
        AND e.allocation_id=NEW.allocation_id AND e.entry_type='ACCRUAL';
    SELECT coalesce(sum(e.amount),0) INTO reversed
      FROM flex_partner_earnings_entries e
      WHERE e.rule_version_id=NEW.rule_version_id
        AND e.allocation_id=NEW.allocation_id AND e.entry_type='REVERSAL';
    IF accrued=0 OR reversed>accrued
       OR reversed>round(accrued*(
          SELECT coalesce(sum(ar.amount),0) FROM flex_allocation_reversals ar
          WHERE ar.allocation_id=NEW.allocation_id
       )/alloc_rec.amount,2) THEN
      RAISE EXCEPTION 'FLEX_PARTNER_OVERREVERSED' USING ERRCODE='23514';
    END IF;
  END IF;

  RETURN NEW;
END $flex$;

CREATE CONSTRAINT TRIGGER flex_qa_partner_earnings_capacity
AFTER INSERT ON flex_partner_earnings_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION flex_qa_partner_earnings_guard();

ALTER TABLE flex_partner_rule_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_partner_rule_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_partner_earnings_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE flex_partner_earnings_entries FORCE ROW LEVEL SECURITY;

CREATE ROLE flex_agent_statement_reader NOLOGIN;
CREATE ROLE flex_investor_statement_reader NOLOGIN;
CREATE ROLE flex_platform_statement_reader NOLOGIN;
GRANT USAGE ON SCHEMA public TO
 flex_agent_statement_reader,flex_investor_statement_reader,flex_platform_statement_reader;
GRANT SELECT ON flex_partner_earnings_entries TO
 flex_agent_statement_reader,flex_investor_statement_reader,flex_platform_statement_reader;

CREATE POLICY flex_agent_statement_own ON flex_partner_earnings_entries
FOR SELECT TO flex_agent_statement_reader
USING (agent_id=NULLIF(current_setting('flex.authorized_agent_id',true),'')::uuid
       AND investor_id IS NULL);
CREATE POLICY flex_investor_statement_own ON flex_partner_earnings_entries
FOR SELECT TO flex_investor_statement_reader
USING (investor_id=NULLIF(current_setting('flex.authorized_investor_id',true),'')::uuid
       AND agent_id IS NULL);
CREATE POLICY flex_admin_statement_all ON flex_partner_earnings_entries
FOR SELECT TO flex_platform_statement_reader USING (true);

-- No grant to any client to create, change or delete statement entries,
-- and no BANK_PAID or VERIFIED payout table is asserted as implemented.
COMMENT ON TABLE flex_partner_earnings_entries IS
 'CI-only accrual/reversal previews, not bank-paid investor or agent commissions';
COMMIT;
