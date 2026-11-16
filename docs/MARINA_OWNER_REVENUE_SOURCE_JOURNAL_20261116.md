# MARINA SMART — immutable source approval journal (P0, Draft)

**Boundary:** This is approval of *verified delivered-service source evidence*, **not** an accounting revenue recognition or profit journal. It never writes to `payments`, suppliers, production stock or historical service rows.

## Operational contract

- OWNER alone can approve `ROOM_NIGHT` and `DINING_ORDER`. A custom `FINANCE` module grant does not promote another role.
- For `ROOM_NIGHT`: CHECKED_OUT reservation, exactly one actual CHECKED_OUT stay, real room assignment, actual local arrival/departure equal to booked dates; one specified service date must be a delivered night. The face value is the reproducible integer-KGS allocation of booked total; package/tax/discount allocation is **not** assumed.
- For `DINING_ORDER`: SERVED order, matching active OPEN/PAID folio by source ID, service date and amount; only one source is approved, and kitchen order + folio are **never added together**.
- API derives source face amount and stores a PostgreSQL JSONB snapshot; client cannot specify the approved monetary value.
- The ID supplied by the client is the durable idempotency key. **Same ID + same content + same OWNER** replays with `already_processed=true`. Changed content or different tenant/owner for that ID produces **409**.
- One initial APPROVE_SOURCE event per (property, source type, source ID, service date). A different ID for the same source/date is **409**, even if the initial approval was later reversed.
- A REVERSE_SOURCE event references exactly one initial approval. Same reversal ID replay is safe, changed payload produces **409**, second reversal with different ID produces **409**.
- PostgreSQL trigger disallows UPDATE and DELETE on the table. No rewriting or erasing journal history, including reversals.
- OWNER report returns approval and reversal counts, active approved room-nights and restaurant orders and **unrecognized** face value, with explicit `recognized_revenue_kgs=null` and `recognized_profit_kgs=null`.

## REST

- `POST /api/v1/admin/finance/owner/revenue-source-events` body
  `{"id":"<client UUID>","source_type":"ROOM_NIGHT","source_id":"<reservation UUID>","service_date":"YYYY-MM-DD","reason":"Checked real stay and room"}`.
- For restaurant `source_type="DINING_ORDER"` and `source_id=<served kitchen order UUID>`.
- `POST /api/v1/admin/finance/owner/revenue-source-events/{approval_id}/reverse` body
  `{"id":"<new client UUID>","reason":"Corrective source review reason"}`.
- `GET /api/v1/admin/finance/owner/revenue-source-events?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` returns append-only events.
- `GET /api/v1/admin/finance/owner/accrual-readiness?... ` includes `source_approval_journal`; owner Finance summary Web/Mobile displays it.

## Exact tests / gates

The disposable local PostgreSQL E2E requires `ALLOW_REVENUE_JOURNAL_SYNTHETIC_CI=1` plus loopback DB and API. It constructs one 1000 som three-night stay and one 350 som served order with matching folio, verifies concurrent eight-way approval/reversal replay, mismatched same ID, one source/date, non-OWNER 403, immutable SQL UPDATE/DELETE prohibition, and no extra customer Payment. The test leaves synthetic sources and approval events **only** in CI's disposable PostgreSQL so immutable audit history never references artificially deleted test evidence. Production must never run this script.

Source integrity/rollback remain additive: historical 47 migrations have unchanged SQL, new `zz123_marina_owner_revenue_source_events_20261116` is SHA256-pinned.

## P0 still required before recognized profit

1. Approve chart of accounts and nightly package component allocation policy; distinguish lodging, bundled dining, discounts and taxes.
2. Durable source-linked, dated, signed **accounting recognition entries** with gross/net, tax, discount, refund and reclassification, a reversal/correction policy and period close/reopen controls.
3. Detect source drift after approval (room price adjustment, canceled folio, refunds) and require reviewed corrective journal entry.
4. Match food production stock consumption to sold, included, complimentary, canceled and lost portions.
5. Separate owner PAYABLE settlements and stock receipt costs from P&L expenses; reconcile taxes, payroll and depreciation.
6. Two-tenant PostgreSQL E2E, Web/Mobile role parity, shared SHA, Expo Go and physical Android acceptance.
7. Until all the above pass: **recognized revenues, expenses and OWNER profit remain null; NO-GO**.

No Ubuntu, ASKA TASH, production, AI/WhatsApp or separate Future Luxury design changes.
