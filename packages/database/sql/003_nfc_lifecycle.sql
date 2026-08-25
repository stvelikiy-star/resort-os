-- NFC bracelet lifecycle invariants.
-- A wallet may have many historical bracelets, but never more than one ACTIVE bracelet.

CREATE UNIQUE INDEX IF NOT EXISTS uq_nfc_bracelets_one_active_per_wallet
  ON "nfc_bracelets" ("walletId")
  WHERE status = 'ACTIVE'::"NfcBraceletStatus";

-- Closing a wallet must not leave an active bracelet able to look valid to operators.
-- The API performs the state transition transactionally; this constraint layer keeps
-- the cardinality invariant independent of API worker concurrency.
CREATE INDEX IF NOT EXISTS idx_nfc_bracelets_wallet_status_issued
  ON "nfc_bracelets" ("walletId", status, "issuedAt" DESC);
