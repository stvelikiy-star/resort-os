-- CI-only two-hotel payment fixtures, created by disposable DB owner.
-- All values are fictional. No real PMS or banking data.
BEGIN;
DO $fixture$
DECLARE
  h record;
  invoice uuid;
  invoice_line uuid;
  agree uuid;
  tax_policy uuid;
  sku_price uuid;
  period_start date := '2026-11-01';
  period_end date := '2026-11-30';
BEGIN
  FOR h IN SELECT id, CASE WHEN display_name='Hotel A' THEN 'FLEX_RLS_A' ELSE 'FLEX_RLS_B' END invoice_number
           FROM flex_hotels WHERE id IN (
            '00000000-0000-0000-0000-00000000000a',
            '00000000-0000-0000-0000-00000000000b'
           ) LOOP
    SELECT id INTO invoice FROM flex_invoices WHERE invoice_number=h.invoice_number;
    IF invoice IS NULL THEN RAISE EXCEPTION 'Missing two-hotel invoice fixtures'; END IF;

    INSERT INTO flex_hotel_links(hotel_id,deployment_id,property_external_id,verified_at)
    VALUES (h.id,'ci-sandbox-'||h.id::text,'ci-property-'||h.id::text,now());
    INSERT INTO flex_commercial_agreement_versions(
      hotel_id,version,currency,state,terms,terms_digest,signed_at,
      signed_by_subject_id,effective_from
    ) VALUES (
      h.id,1,'KGS','SIGNED','{"QA":"sandbox only"}',repeat('a',64),
      now(),'administrator','2026-11-01'
    ) RETURNING id INTO agree;
    INSERT INTO flex_tax_policy_versions(
      hotel_id,agreement_version_id,version,treatment,rate_bps,
      approval_reference,approved_by,approved_at,valid_from
    ) VALUES (h.id,agree,1,'EXEMPT',0,'QA-NO-REAL-TAX','administrator',
      now(),'2026-11-01')
    RETURNING id INTO tax_policy;

    SELECT id INTO sku_price FROM flex_price_versions WHERE sku='BASE_PMS' AND version=1;
    UPDATE flex_invoice_lines SET price_version_id=sku_price
       WHERE invoice_id=invoice;
    SELECT id INTO invoice_line FROM flex_invoice_lines WHERE invoice_id=invoice LIMIT 1;

    INSERT INTO flex_issued_invoice_records(
      invoice_id,hotel_id,agreement_version_id,tax_policy_version_id,
      period_start,period_end,quote_digest,issuance_digest,
      net_amount,tax_amount,total_amount
    )
    SELECT invoice,h.id,agree,tax_policy,period_start,period_end,
           md5(h.id::text)||md5(invoice::text),
           md5(invoice::text)||md5(h.id::text),
           total,0,total FROM flex_invoices WHERE id=invoice;

    INSERT INTO flex_issued_invoice_line_tax(
      invoice_id,invoice_line_id,net_amount,tax_amount,payable_amount
    )
    SELECT invoice,invoice_line,total,0,total FROM flex_invoices WHERE id=invoice;
  END LOOP;
  SET CONSTRAINTS flex_issued_invoice_document_capacity IMMEDIATE;
END
$fixture$;

INSERT INTO flex_payment_intents(
  id,invoice_id,provider,external_intent_id,requested_amount,currency,state
)
VALUES
 ('00000000-0000-0000-0000-000000001001',
  (SELECT id FROM flex_invoices WHERE invoice_number='FLEX_RLS_A'),
  'FLEX_QA_SIMULATOR','qa_intent_a_1',60.00,'KGS','READY'),
 ('00000000-0000-0000-0000-000000001002',
  (SELECT id FROM flex_invoices WHERE invoice_number='FLEX_RLS_A'),
  'FLEX_QA_SIMULATOR','qa_intent_a_2',50.00,'KGS','READY'),
 ('00000000-0000-0000-0000-000000001003',
  (SELECT id FROM flex_invoices WHERE invoice_number='FLEX_RLS_B'),
  'FLEX_QA_SIMULATOR','qa_intent_b_1',200.00,'KGS','READY');
COMMIT;
