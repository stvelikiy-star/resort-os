# MARINA SMART — OWNER accrual source-readiness (P0, Draft)

**Scope:** isolated branch based on #537. No production/Ubuntu/ASKA TASH changes.
**Status:** PRE-RECOGNITION SOURCES. This report does **not** calculate recognized profit.

## Fact boundaries

| Fact | Stored source | What the report can say | What it cannot say |
| --- | --- | --- | --- |
| Guest money received | `payments.status=RECEIVED` | Cash fact | Earned service revenue |
| Accommodation | `reservations.status=CHECKED_OUT` | Booked face value candidate | Earned amount per occupied night / refunded and repriced net revenue |
| Restaurant | `kitchen_orders.status=SERVED` | Delivered order face value candidate | Recognized sales, taxes or margin |
| Guest folio | `guest_folio_charges` | Open/paid source receivables; disputed/undated sources | Earned revenue without service proof |
| Kitchen COGS | `kitchen_stock_movements.kind=PRODUCTION` | Immutable input consumed for preparation | Cost of *sold* plates or period-end food COGS |
| Spoilage and waste | `kind IN ('WASTE','SPOILAGE')` | Separately measured stock losses | Supplier cash expenditure |
| Supplier invoice | `kitchen_supplier_documents` | Source obligation | P&L expense or money received |
| Supplier settlement | `kitchen_supplier_settlements` | Recorded supplier cash fact | Incremental P&L cost |
| Supplier return | `kitchen_supplier_returns` | Supplier credit at invoice price; stock debit at moving average | Automatically recognized return profit |
| OWNER general expenses | `owner_expenses.status=POSTED` | Dated obligations by category | A separate *second* stock expense for any product purchase |

### Source combination limits

- All expense and sale **candidates are non-additive**. A served kitchen order and its folio charge represent the same underlying transaction. No total revenue is inferred.
- SUPPLIES and OTHER require review: they may overlap procurement. A matching supplier name/reference raises a probable-duplicate signal; it does not trigger rewriting or automatic netting.
- Production costs are material consumed on preparation; matching food cost to served/cancelled/complimentary portions is a separate source allocation exercise.
- Posted nonstock owner expenses are *candidates*, pending period, accrual basis and related taxes verification. Manual settlements do not increase the candidate amount.
- Legacy receipt prices are not repriced retroactively. Supplier credit minus moving-average stock cost needs a documented correction journal.
- Accommodation must be recognized by delivered room nights with cancellation, date/time zones, room moves, discounts and refunds reconciliation. CHECKED_OUT face value is not an earnings posting.
- Received payments, reservations, folio charges, and supplier settlements cannot be used as one naive cash-minus-cost profit calculation.

## Acceptance before removing `REQUIRES_APPROVED_RECOGNITION_LEDGER`

1. Approved chart of accounts, classification for stock vs operating obligations, and a dated immutable recognition journal with source IDs and reversal IDs.
2. Deterministic service-night/folio recognition with tax and refund adjustments; idempotent event posting and verified multi-property isolation.
3. Matched production-cost allocations to services sold, non-sale meals, waste, spoilage, returned goods and opening balances.
4. Double-entry reconciliation: revenue journal, expense journal, supplier payables, customer receivables, bank/cash records and inventory all balance in PostgreSQL on one SHA.
5. Financial data migration and rollback/restore rehearsal, independent reconciliation, sign-off by responsible accountant; only then expose recognized profit.
6. CI, E2E Web/API/DB, Expo Go and physical Android acceptance all PASS.

## Current delivered API

- `GET /api/v1/admin/finance/owner/accrual-readiness?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` (OWNER only).
- `GET /api/v1/admin/finance/summary` adds `owner_accrual_readiness_snapshot` **for OWNER only**.
- Date range max 367 calendar days, property-local time, `REPEATABLE READ` read-only transaction.
- All recognized totals return **null**, with immutable-source candidates, counts, exact KGS strings, explicit blockers and false flags for payment=income/receipt=expense.

This is a usable control report; it is intentionally **not** an accepted P&L.
