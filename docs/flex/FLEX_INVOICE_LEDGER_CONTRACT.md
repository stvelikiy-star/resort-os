# MARINA SMART FLEX — invoice issuance and cash ledger: technical preview

Status: **isolated development / disposable PostgreSQL only**. Not a bank, not a fiscal receipt, not a public billing API; no changes to operational MARINA SMART.

## Delivered code
- `app/flex_billing.py`: strict, pure invoice issuance plan requiring signed agreement, verified hotel link, explicit approved tax profile; deterministic price/amount/fiscal snapshot; KGS decimal arithmetic.
- `plan_payment_application()`: only verified external confirmation *evidence* yields allocation proposals; divides paid amount per invoice line (SKU), leaves overpayment as unallocated credit.
- `0007_flex_invoice_ledger_preview.sql`: versioned hotel tax policy with approval, append-only issued invoice snapshot, every invoice line net/tax/gross, uniqueness per contract-period, deferred document balance checks and immutability of finalized invoices.
- Existing `flex_provider_events` unique by provider/event ID and `flex_confirmed_payments` unique by provider/payment ID; `flex_payment_allocations` protect against exceeding payment and per-line charges.
- `flex_verified_invoice_balances` is a **private, unadjusted** internal view. Refund reversals must be applied before interpreting outstanding debt.
- Separate CI Python and Postgres negative tests for cross-hotel payment, duplicate payment ID, over-allocation, line rewriting, unbalanced issuance and reissued same contract-period.

## Non-negotiable gate before real invoices
1. Approved company fiscal requirements, invoice numbering, date/timezone, KGS tax regimes and legal documents. Sample 12% in CI is **fictional**.
2. DB-backed contract signatures, immutable canonical SKU/discount/period price versions; review of prior grandfathered customers.
3. Dedicated billing writer with non-inherited privileges, RLS, MFA, double-control rules and verified issuer claims. Current SQL fixtures run as CI database owner only; **NOT a secure public invoice creation endpoint**.
4. Proper provider adapter verifying official signatures/transaction settlement, replay, refund/cancellation/partial and chargeback; no signature verification code for real provider exists.
5. Consistent manual 2-person exception workflow; never mark cash paid from uploaded QR screenshot.
6. Tests of multi-writer concurrency, backup/restore and independent QA rollback.
7. Release RC Truth must approve new commercial scope through a reviewed release process; do not bypass freeze checks.

## Ledger invariant
The unit of paid subscription revenue is an **invoice line allocation**, not UI feature enablement or a payment notification. A bank payment is only confirmed through verified provider evidence. Agent commissions/investor accruals will consume confirmed and reconciled allocations, with reversals as new records. They must not treat gross invoice billing as cash received.

A single invoice can have:
- net contractual price,
- tax computed from a specifically approved rule,
- total to pay,
- one or more confirmed receipts,
- payments split across SKU lines,
- unallocated credit, never silently recognized as module revenue.

## Current limitations
`app/flex_billing.py` produces plans and accepts evidence booleans only for **trusted, test-controlled callers**; it is not wired to a bank, external API or production DB. The 0007 schema is a preliminary design. It does not establish Kyrgyz tax law compliance or a real commercial invoice. Production invoice status/payment balances need net refunds and credit notes, ledger-locking transactions, reconciliation and audit.

No QR URL, live invoices, payment capture, subscriptions activation, investor payouts or hotel suspension have been enabled. All production and PMS settings remain unchanged.

## Next PR
Payment settlement adapter with realistic test-only provider signatures, transactional event idempotency, refund/chargeback bound checks and independently verified payment reconciler. Then secured invoice writer/API and full E2E in a dedicated central QA database.
