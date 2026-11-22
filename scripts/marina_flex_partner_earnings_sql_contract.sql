-- MARINA FLEX partner earnings: disposable two-hotel acceptance.
-- Only QA_SIMULATOR receipts, no agent or investor bank disbursements.
BEGIN;
DO $fixture$
DECLARE
  h_a uuid:='00000000-0000-0000-0000-00000000000a';
  h_b uuid:='00000000-0000-0000-0000-00000000000b';
  i_a uuid; i_b uuid; a_a uuid; a_b uuid; p_a uuid; p_b uuid;
  ag_a uuid; ag_b uuid; inv_a uuid; inv_b uuid;
  contract_a uuid; contract_b uuid;
  ar_a uuid; ar_b uuid; ir_a uuid; ir_b uuid;
  refund uuid; reversal uuid;
BEGIN
  SELECT id INTO i_a FROM flex_invoices WHERE invoice_number='FLEX_RLS_A';
  SELECT id INTO i_b FROM flex_invoices WHERE invoice_number='FLEX_RLS_B';
  IF i_a IS NULL OR i_b IS NULL THEN RAISE EXCEPTION 'Missing commercial hotel fixture'; END IF;

  INSERT INTO flex_platform_memberships(subject_id,role,active)
    VALUES('sales-2','SALES_AGENT',true),('investor-2','INVESTOR',true);
  SELECT id INTO ag_a FROM flex_agents WHERE platform_subject_id='sales-1';
  SELECT id INTO inv_a FROM flex_investors WHERE platform_subject_id='investor-1';
  INSERT INTO flex_agents(platform_subject_id,status) VALUES('sales-2','ACTIVE') RETURNING id INTO ag_b;
  INSERT INTO flex_investors(platform_subject_id,status) VALUES('investor-2','ACTIVE') RETURNING id INTO inv_b;

  INSERT INTO flex_investor_contract_versions(
    investor_id,contract_key,version,principal,share_bps,terms,effective_from
  ) VALUES (inv_a,'QA_INV_CONTRACT_A',1,1000.00,3000,'{"qa_only":true}','2026-01-01')
    RETURNING id INTO contract_a;
  INSERT INTO flex_investor_contract_versions(
    investor_id,contract_key,version,principal,share_bps,terms,effective_from
  ) VALUES (inv_b,'QA_INV_CONTRACT_B',1,2000.00,2500,'{"qa_only":true}','2026-01-01')
    RETURNING id INTO contract_b;

  SELECT id INTO p_a FROM flex_invoice_lines WHERE invoice_id=i_a LIMIT 1;
  SELECT id INTO p_b FROM flex_invoice_lines WHERE invoice_id=i_b LIMIT 1;
  IF p_a IS NULL OR p_b IS NULL THEN RAISE EXCEPTION 'Missing SKU items'; END IF;

  INSERT INTO flex_confirmed_payments(
     hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES(h_a,i_a,'FLEX_QA_SIMULATOR','QA_AGENT_INVESTOR_PAY_A',100.00,'KGS',now())
    RETURNING id INTO a_a;
  INSERT INTO flex_confirmed_payments(
     hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at
  ) VALUES(h_b,i_b,'FLEX_QA_SIMULATOR','QA_AGENT_INVESTOR_PAY_B',200.00,'KGS',now())
    RETURNING id INTO a_b;
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(i_a,a_a,p_a,100.00) RETURNING id INTO p_a;
  INSERT INTO flex_payment_allocations(invoice_id,payment_id,invoice_line_id,amount)
    VALUES(i_b,a_b,p_b,200.00) RETURNING id INTO p_b;

  INSERT INTO flex_partner_rule_versions(
    hotel_id,sku,agent_id,version,rate_bps,approved_by,approval_digest,effective_from
  ) VALUES(h_a,'BASE_PMS',ag_a,1,1000,'QA_APPROVER',repeat('a',64),'2026-01-01')
    RETURNING id INTO ar_a;
  INSERT INTO flex_partner_rule_versions(
    hotel_id,sku,agent_id,version,rate_bps,approved_by,approval_digest,effective_from
  ) VALUES(h_b,'BASE_PMS',ag_b,1,1000,'QA_APPROVER',repeat('b',64),'2026-01-01')
    RETURNING id INTO ar_b;
  INSERT INTO flex_partner_rule_versions(
    hotel_id,sku,investor_id,investor_contract_version_id,
    version,rate_bps,approved_by,approval_digest,effective_from
  ) VALUES(h_a,'BASE_PMS',inv_a,contract_a,1,3000,'QA_APPROVER',repeat('c',64),'2026-01-01')
    RETURNING id INTO ir_a;
  INSERT INTO flex_partner_rule_versions(
    hotel_id,sku,investor_id,investor_contract_version_id,
    version,rate_bps,approved_by,approval_digest,effective_from
  ) VALUES(h_b,'BASE_PMS',inv_b,contract_b,1,2500,'QA_APPROVER',repeat('d',64),'2026-01-01')
    RETURNING id INTO ir_b;

  INSERT INTO flex_partner_earnings_entries(
     rule_version_id,agent_id,allocation_id,entry_type,amount
  ) VALUES(ar_a,ag_a,p_a,'ACCRUAL',10.00),
          (ar_b,ag_b,p_b,'ACCRUAL',20.00);
  INSERT INTO flex_partner_earnings_entries(
     rule_version_id,investor_id,allocation_id,entry_type,amount
  ) VALUES(ir_a,inv_a,p_a,'ACCRUAL',30.00),
          (ir_b,inv_b,p_b,'ACCRUAL',50.00);
  SET CONSTRAINTS flex_qa_partner_earnings_capacity IMMEDIATE;

  INSERT INTO flex_payment_reversals(payment_id,external_reversal_key,amount,reason)
  VALUES(a_a,'QA_INVESTOR_REFUND_A',20.00,'CI_PARTIAL_REFUND')
    RETURNING id INTO refund;
  INSERT INTO flex_allocation_reversals(reversal_id,allocation_id,amount)
  VALUES(refund,p_a,20.00) RETURNING id INTO reversal;
  SET CONSTRAINTS flex_refund_cash_capacity,flex_refund_allocated_capacity IMMEDIATE;

  INSERT INTO flex_partner_earnings_entries(
     rule_version_id,agent_id,allocation_id,
     source_allocation_reversal_id,entry_type,amount
  ) VALUES(ar_a,ag_a,p_a,reversal,'REVERSAL',2.00);
  INSERT INTO flex_partner_earnings_entries(
     rule_version_id,investor_id,allocation_id,
     source_allocation_reversal_id,entry_type,amount
  ) VALUES(ir_a,inv_a,p_a,reversal,'REVERSAL',6.00);
  SET CONSTRAINTS flex_qa_partner_earnings_capacity IMMEDIATE;

  -- No duplicate accrual for the same contract version and allocated cash.
  BEGIN
    INSERT INTO flex_partner_earnings_entries(
      rule_version_id,agent_id,allocation_id,entry_type,amount
    ) VALUES(ar_a,ag_a,p_a,'ACCRUAL',10);
    RAISE EXCEPTION 'CI_DUPLICATE_AGENT_EARNINGS_ACCEPTED';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- Cross-hotel agent cannot claim the other's receipt.
  BEGIN
    INSERT INTO flex_partner_earnings_entries(
      rule_version_id,agent_id,allocation_id,entry_type,amount
    ) VALUES(ar_b,ag_b,p_a,'ACCRUAL',1);
    SET CONSTRAINTS flex_qa_partner_earnings_capacity IMMEDIATE;
    RAISE EXCEPTION 'CI_CROSS_HOTEL_AGENT_EARNINGS_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM <> 'FLEX_PARTNER_SCOPE_OR_SOURCE_INVALID' THEN RAISE; END IF;
  END;

  -- Same receipt cannot promise more than its tax-excluded cash after
  -- adding another contract: no agent + investor overcommit.
  BEGIN
    INSERT INTO flex_partner_rule_versions(
      hotel_id,sku,agent_id,version,rate_bps,approved_by,approval_digest,effective_from
    ) VALUES(h_a,'BASE_PMS',ag_a,2,9000,'QA_APPROVER',repeat('e',64),'2026-01-01')
    RETURNING id INTO ar_b;
    INSERT INTO flex_partner_earnings_entries(
      rule_version_id,agent_id,allocation_id,entry_type,amount
    ) VALUES(ar_b,ag_a,p_a,'ACCRUAL',90.00);
    SET CONSTRAINTS flex_qa_partner_earnings_capacity IMMEDIATE;
    RAISE EXCEPTION 'CI_OVERCOMMITTED_PARTNER_REVENUE_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM <> 'FLEX_PARTNER_COMBINED_OVERCOMMIT' THEN RAISE; END IF;
  END;

  -- A reversal must be backed by the SAME allocation and not exceed
  -- pro-rata share of the source refund.
  BEGIN
    INSERT INTO flex_partner_earnings_entries(
      rule_version_id,investor_id,allocation_id,source_allocation_reversal_id,entry_type,amount
    ) VALUES(ir_b,inv_b,p_b,reversal,'REVERSAL',1.00);
    SET CONSTRAINTS flex_qa_partner_earnings_capacity IMMEDIATE;
    RAISE EXCEPTION 'CI_WRONG_ALLOCATION_REVERSAL_ACCEPTED';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM <> 'FLEX_PARTNER_REVERSAL_WRONG_SOURCE' THEN RAISE; END IF;
  END;

  -- Fund is not the same as paid payout: the QA ledger must NEVER include
  -- an actual bank-disbursement event.
  IF (SELECT count(*) FROM flex_partner_earnings_entries)!=6 THEN
    RAISE EXCEPTION 'CI_UNEXPECTED_QA_PARTNER_ENTRIES';
  END IF;
END
$fixture$;
COMMIT;

-- Default deny and tenant/party-scoped RLS checks.
BEGIN;
SET LOCAL ROLE flex_agent_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=0 THEN 1 ELSE 0 END;
ROLLBACK;

BEGIN;
SELECT set_config('flex.authorized_agent_id',
  (SELECT id::text FROM flex_agents WHERE platform_subject_id='sales-1'),true);
SET LOCAL ROLE flex_agent_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=2 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT sum(CASE WHEN entry_type='ACCRUAL' THEN amount ELSE -amount END)
                     FROM flex_partner_earnings_entries)=8.00 THEN 1 ELSE 0 END;
ROLLBACK;

BEGIN;
SELECT set_config('flex.authorized_investor_id',
  (SELECT id::text FROM flex_investors WHERE platform_subject_id='investor-1'),true);
SET LOCAL ROLE flex_investor_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=2 THEN 1 ELSE 0 END;
SELECT 1 / CASE WHEN (SELECT sum(CASE WHEN entry_type='ACCRUAL' THEN amount ELSE -amount END)
                     FROM flex_partner_earnings_entries)=24.00 THEN 1 ELSE 0 END;
ROLLBACK;

BEGIN;
SET LOCAL ROLE flex_platform_statement_reader;
SELECT 1 / CASE WHEN (SELECT count(*) FROM flex_partner_earnings_entries)=6 THEN 1 ELSE 0 END;
ROLLBACK;
