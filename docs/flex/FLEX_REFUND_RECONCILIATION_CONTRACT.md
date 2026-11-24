# MARINA FLEX — refund-adjusted commercial cash ledger

Status: isolated **QA-only draft**. No payment or refund provider connected. Tests use fictional amounts in a disposable PostgreSQL instance.

## Accounting rule
A commercial payment can be applied across individual invoice lines (paid SKU entitlements). A subsequent refund/chargeback must be recorded as a **new immutable payment reversal**, and any previously credited SKU allocation must be reduced by a separately linked **allocation reversal**. Original rows are never updated or deleted.

SQL `0008_flex_refund_reconciliation_preview.sql` provides deferred, transactional checks:
- refund total <= original bank-confirmed receipt;
- allocation reversal <= original paid line allocation;
- allocation reversals linked to **the same** confirmed payment as the refund event;
- reverse a portion of a paid SKU whenever remaining confirmed cash no longer covers it;
- a refund may consume the hotel's unapplied cash credit first;
- do not permit allocating more money after a refund than cash actually remains;
- reconciliation view computes net cash, net applied revenue, outstanding and unapplied credit independently.

**Worked CI example (not real hotel)**: invoice A 100.00 KGS, payment 120.00, SKU allocated 100.00, credit 20.00. First refund 10.00 reduces credit to 10.00. Second refund 50.00 requires reversing 40.00 of SKU allocation; after both refunds: net bank cash 60.00, credited SKU revenue 60.00, outstanding 40.00, credit 0.00. Agents and investors must accrue only on eligible net revenue.

## Still required before the production payment engine
- Official provider API credentials, signed settlement webhooks, request verification, event IDs and refund success evidence; no provider integration in this PR.
- Single restricted transactional service role, idempotent provider settlement import, end-to-end row locking, retries/reconciliation, watchdogs, audit and role separation.
- Real bank refund must be verified before writing refund event; SQL does not itself move or validate money.
- Financial export/dashboard formulas must define whether taxes and provider fees are part of commission/investor bases.
- Independent migration/backups, two-tenant RLS, concurrency and disaster-recovery testing.
- Existing customers' terms remain unchanged; no live suspension, no QR money collection.

Files: `docs/flex/sql/0008_flex_refund_reconciliation_preview.sql`, `scripts/marina_flex_refund_reconciliation_sql_contract.sql`, isolated CI workflow. No PMS or Production changes.
