-- Three Crowns NFC wallet and beach payment invariants.
-- Critical monetary logic stays in PostgreSQL so retries/concurrency cannot bypass it.

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'property_beach_commission_valid') THEN
    ALTER TABLE "properties"
      ADD CONSTRAINT property_beach_commission_valid
      CHECK ("beachCommissionBps" >= 0 AND "beachCommissionBps" <= 10000);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nfc_wallet_nonnegative_balance') THEN
    ALTER TABLE "nfc_wallets"
      ADD CONSTRAINT nfc_wallet_nonnegative_balance CHECK ("balanceKgs" >= 0);
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nfc_transaction_positive_amount') THEN
    ALTER TABLE "nfc_transactions"
      ADD CONSTRAINT nfc_transaction_positive_amount CHECK ("amountKgs" > 0),
      ADD CONSTRAINT nfc_transaction_nonnegative_commission CHECK ("hotelCommissionKgs" >= 0),
      ADD CONSTRAINT nfc_transaction_nonnegative_partner_net CHECK ("partnerNetKgs" >= 0),
      ADD CONSTRAINT nfc_transaction_commission_valid CHECK ("commissionBps" >= 0 AND "commissionBps" <= 10000),
      ADD CONSTRAINT nfc_transaction_split_matches CHECK ("hotelCommissionKgs" + "partnerNetKgs" = "amountKgs");
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nfc_ledger_balance_math') THEN
    ALTER TABLE "nfc_ledger_entries"
      ADD CONSTRAINT nfc_ledger_balance_nonnegative CHECK ("balanceBeforeKgs" >= 0 AND "balanceAfterKgs" >= 0),
      ADD CONSTRAINT nfc_ledger_balance_math CHECK ("balanceBeforeKgs" + "deltaKgs" = "balanceAfterKgs");
  END IF;
END $$;

CREATE OR REPLACE FUNCTION process_nfc_payment(
  p_property_code text,
  p_bracelet_uid_hash text,
  p_partner_staff_user uuid,
  p_amount_kgs integer,
  p_idempotency_key text,
  p_description text DEFAULT NULL
)
RETURNS TABLE (
  transaction_id uuid,
  wallet_id uuid,
  balance_before_kgs integer,
  balance_after_kgs integer,
  amount_kgs integer,
  hotel_commission_kgs integer,
  partner_net_kgs integer,
  commission_bps integer,
  idempotent_replay boolean
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_property_id uuid;
  v_commission_bps integer;
  v_bracelet_id uuid;
  v_bracelet_status text;
  v_wallet_id uuid;
  v_wallet_status text;
  v_balance_before integer;
  v_balance_after integer;
  v_hotel_commission integer;
  v_partner_net integer;
  v_transaction_id uuid;
  v_existing_transaction uuid;
  v_existing_partner uuid;
  v_existing_wallet uuid;
  v_existing_before integer;
  v_existing_after integer;
  v_existing_amount integer;
  v_existing_commission integer;
  v_existing_net integer;
  v_existing_bps integer;
BEGIN
  IF p_amount_kgs IS NULL OR p_amount_kgs <= 0 THEN
    RAISE EXCEPTION 'NFC_INVALID_AMOUNT' USING ERRCODE = 'P0001';
  END IF;
  IF p_idempotency_key IS NULL OR length(trim(p_idempotency_key)) < 8 THEN
    RAISE EXCEPTION 'NFC_INVALID_IDEMPOTENCY_KEY' USING ERRCODE = 'P0001';
  END IF;

  SELECT p.id, p."beachCommissionBps"
    INTO v_property_id, v_commission_bps
  FROM "properties" p
  WHERE p.code = p_property_code;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NFC_PROPERTY_NOT_FOUND' USING ERRCODE = 'P0001';
  END IF;

  -- Authorization happens before any replay lookup so one partner cannot use a
  -- guessed idempotency key to read another partner's transaction result.
  PERFORM 1
  FROM "staff_users" u
  WHERE u.id = p_partner_staff_user
    AND u."propertyId" = v_property_id
    AND u."isActive" = true
    AND u.role = 'BEACH_PARTNER'::"StaffRole";

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NFC_PARTNER_NOT_AUTHORIZED' USING ERRCODE = 'P0001';
  END IF;

  -- Fast replay path. Original before/after balances come from the immutable ledger,
  -- not the wallet's current balance after later transactions.
  SELECT t.id, t."partnerStaffUserId", t."walletId", l."balanceBeforeKgs", l."balanceAfterKgs",
         t."amountKgs", t."hotelCommissionKgs", t."partnerNetKgs", t."commissionBps"
    INTO v_existing_transaction, v_existing_partner, v_existing_wallet, v_existing_before, v_existing_after,
         v_existing_amount, v_existing_commission, v_existing_net, v_existing_bps
  FROM "nfc_transactions" t
  LEFT JOIN "nfc_ledger_entries" l ON l."transactionId" = t.id
  WHERE t."propertyId" = v_property_id
    AND t."idempotencyKey" = p_idempotency_key;

  IF FOUND THEN
    IF v_existing_partner <> p_partner_staff_user THEN
      RAISE EXCEPTION 'NFC_IDEMPOTENCY_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
    RETURN QUERY SELECT
      v_existing_transaction, v_existing_wallet, v_existing_before, v_existing_after,
      v_existing_amount, v_existing_commission, v_existing_net, v_existing_bps, true;
    RETURN;
  END IF;

  -- Serialize every operation for this bracelet/wallet. Different API workers and
  -- simultaneous smartphone taps therefore observe one balance in a strict order.
  SELECT b.id, b.status::text, w.id, w.status::text, w."balanceKgs"
    INTO v_bracelet_id, v_bracelet_status, v_wallet_id, v_wallet_status, v_balance_before
  FROM "nfc_bracelets" b
  JOIN "nfc_wallets" w ON w.id = b."walletId"
  WHERE b."propertyId" = v_property_id
    AND b."uidHash" = p_bracelet_uid_hash
  FOR UPDATE OF b, w;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'NFC_BRACELET_NOT_FOUND' USING ERRCODE = 'P0001';
  END IF;
  IF v_bracelet_status <> 'ACTIVE' THEN
    RAISE EXCEPTION 'NFC_BRACELET_NOT_ACTIVE' USING ERRCODE = 'P0001';
  END IF;
  IF v_wallet_status <> 'ACTIVE' THEN
    RAISE EXCEPTION 'NFC_WALLET_NOT_ACTIVE' USING ERRCODE = 'P0001';
  END IF;

  -- A concurrent identical retry may have completed while we waited for the wallet lock.
  SELECT t.id, t."partnerStaffUserId", t."walletId", l."balanceBeforeKgs", l."balanceAfterKgs",
         t."amountKgs", t."hotelCommissionKgs", t."partnerNetKgs", t."commissionBps"
    INTO v_existing_transaction, v_existing_partner, v_existing_wallet, v_existing_before, v_existing_after,
         v_existing_amount, v_existing_commission, v_existing_net, v_existing_bps
  FROM "nfc_transactions" t
  LEFT JOIN "nfc_ledger_entries" l ON l."transactionId" = t.id
  WHERE t."propertyId" = v_property_id
    AND t."idempotencyKey" = p_idempotency_key;

  IF FOUND THEN
    IF v_existing_partner <> p_partner_staff_user THEN
      RAISE EXCEPTION 'NFC_IDEMPOTENCY_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
    RETURN QUERY SELECT
      v_existing_transaction, v_existing_wallet, v_existing_before, v_existing_after,
      v_existing_amount, v_existing_commission, v_existing_net, v_existing_bps, true;
    RETURN;
  END IF;

  IF v_balance_before < p_amount_kgs THEN
    RAISE EXCEPTION 'NFC_INSUFFICIENT_FUNDS' USING ERRCODE = 'P0001';
  END IF;

  v_hotel_commission := round((p_amount_kgs::numeric * v_commission_bps::numeric) / 10000)::integer;
  v_partner_net := p_amount_kgs - v_hotel_commission;
  v_balance_after := v_balance_before - p_amount_kgs;
  v_transaction_id := gen_random_uuid();

  UPDATE "nfc_wallets"
  SET "balanceKgs" = v_balance_after, "updatedAt" = now()
  WHERE id = v_wallet_id;

  INSERT INTO "nfc_transactions" (
    id, "propertyId", "walletId", "braceletId", "partnerStaffUserId",
    "amountKgs", "hotelCommissionKgs", "partnerNetKgs", "commissionBps",
    status, "idempotencyKey", description, "createdAt"
  ) VALUES (
    v_transaction_id, v_property_id, v_wallet_id, v_bracelet_id, p_partner_staff_user,
    p_amount_kgs, v_hotel_commission, v_partner_net, v_commission_bps,
    'COMPLETED', p_idempotency_key, p_description, now()
  );

  INSERT INTO "nfc_ledger_entries" (
    id, "walletId", "transactionId", "entryType", "deltaKgs",
    "balanceBeforeKgs", "balanceAfterKgs", note, "createdAt"
  ) VALUES (
    gen_random_uuid(), v_wallet_id, v_transaction_id, 'BEACH_CHARGE', -p_amount_kgs,
    v_balance_before, v_balance_after, p_description, now()
  );

  RETURN QUERY SELECT
    v_transaction_id, v_wallet_id, v_balance_before, v_balance_after,
    p_amount_kgs, v_hotel_commission, v_partner_net, v_commission_bps, false;
END;
$$;
