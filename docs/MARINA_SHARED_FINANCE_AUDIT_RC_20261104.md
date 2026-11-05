# MARINA SMART — P0 hotel-local finance and audit read acceptance (2026-11-04)

**Status:** DRAFT, isolated two-hotel staging only, NOT external production.
Source parent: shared-auth and 12-role ceiling PR #319 at
`8f1d7a2ef6c371a44be62f1c94e930d61d7ce8e9` (38/38 CI PASS).
This branch changes **no database migrations** and introduces **no new API**.

## Canonical existing routes enabled in shared preview

- `GET /api/v1/admin/finance/summary?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`:
  existing `hotel_finance.py` property-scoped report for OWNER/MANAGER
  with FINANCE module. Both dates required; dates are **hotel-local**.
  Runtime converts them to UTC-naive database timestamp boundaries;
  permitted range <=367 calendar days. Report labels `scope.internal_only=true`,
  includes received-only payment facts, methods, debtor snapshot, exception
  flags and a capped reservation ledger preview with truthful truncation metadata.
  **Not** acquired bank funds, revenue recognition, tax ledger or refund settlement.
- `GET /api/v1/ops/tasks/{task_uuid}/history`:
  existing `operations_history.py` property-scoped task audit, OWNER/MANAGER
  with OPS module. Task must belong to selected property's authenticated
  session, foreign UUID returns 404. Bounded 500 newest/ordered audit rows.

All other finance writes, payment collection, refund APIs, room overrides
and unrelated task methods remain **503 in isolated shared preview**. No
`POST` finance endpoint is opened by this change. Shared role ceilings
and per-request live staff permissions from PR #319 remain authoritative.

## Proof required on final SHA

- Browser HTTP session of OWNER in two independent hotels:
  finance summary reports exactly 1 received internal manual payment each,
  1000 KGS for HOTEL_A, 1500 KGS for HOTEL_B; does not reveal the other
  hotel's reservation, payment or guest ledger.
- For each hotel, task history contains ASSIGN/CLAIM/STATUS_CHANGE on its
  own maintenance task; other hotel's task UUID returns 404; unreviewed
  finance mutation returns 503.
- All 12 roles × two hotels must enforce OWNER/MANAGER-only finance/history.
  Manager's FINANCE and OPS grants can be revoked by its own owner; revoked
  session returns 401, fresh login receives 403 on disallowed module,
  HOTEL_B manager remains unaffected.
- Server → real Next Admin → disposable PostgreSQL 16, plus separate
  canonical FastAPI/PostgreSQL role matrix, SQL receipt proofs, source
  guard and required CI on one exact final SHA.

**Unverified:** any external staging/production, financial reconciliation
to a bank, online payments/refunds, original payment provider settlement,
tax compliance, high-volume report performance, live audit retention or
server restoration. A green synthetic CI is not a production release GO.

Main platform only. Do not touch `apps/mobile`, DEMO, shared staging
production settings, Ubuntu or customer database. Do not merge to main.
