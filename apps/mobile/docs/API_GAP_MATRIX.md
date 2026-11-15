# API gap register — 15 November 2026

Current source inventory: [ROLE_SCREEN_MATRIX.md](ROLE_SCREEN_MATRIX.md). Green baseline #519: `7c6b10753cca9651a7bb9a0e161ea23af11d285a` (34/34 workflow runs SUCCESS). The former snapshot `34d705d2` is historical and must not be used to describe current implementation.

| Priority | Confirmed issue | Required resolution / evidence |
|---|---|---|
| P0 | AGENT service UI calls an endpoint whose baseline role dependency excludes ordinary AGENT | This branch narrows POST permission to PMS-enabled ACTIVE linked agents and their own reservation; keep GET queue denied, including custom SERVICES grants. Verify real PostgreSQL persistence and denial cases in Guest Services CI. |
| P0 | AGENT can add services only before leaving new-booking result | This branch reuses the durable service panel in the own-reservation PMS preview. Backend remains authoritative on deep-link/tampered IDs. |
| P0 follow-up implemented | AGENT own service status/date/time/note gap | This branch adds reservation-bound GET readback, PMS/ACTIVE membership/ownership checks, response minimization, date/time/note fields and backward-compatible pending schedule journal. New PostgreSQL/API and mobile CI acceptance still required on its SHA. Ambiguous writes stay blocked until explicit review. |
| P0 security fixed in source | OWNER financial endpoints could accept legacy custom FINANCE grants on another role | All three OWNER dependencies now use module_grant=False. Tests deny 11 non-owner roles on reads, expense creation, settlement and VOID. Existing OWNER positive PostgreSQL E2E must remain green. |
| P0 open | Direct stock receipts can duplicate after timeout/restart | Store already contains procurement receipts (the earlier matrix was wrong). Direct receipts create a new server UUID per call; add stable receipt IDs and persistent pending/reconciliation, preserving existing workflows. |
| P0 | OWNER reports record movements but do not recognize revenue/expenses for profit | Define and implement accrual periods, refunds, service delivery and inventory cost attribution; never rename received-payments difference to profit. |
| P0 | Role inventory was stale (STORE blocked despite implementation, kitchen/finance omitted; DINING_STAFF absent) | Replaced with source operation inventory. Physical acceptance remains open. |
| P0 | Wider Web operations not all available on mobile | See each explicit role gap in the inventory; prioritize operational roles, retain existing functionality. |
| P0 | Single candidate runtime and database evidence incomplete | Re-run Mobile/Web/API/PostgreSQL checks on the final integration SHA after functional fixes. |
| Final | Expo Go / physical Android not yet verified | Device execution, network/restart/revocation and visual acceptance on final candidate. APK build is not device acceptance. |

No new hotel picker, no deployment to Ubuntu/Aska Tash, no AI or WhatsApp activation. Existing endpoints and canonical OperationalTask storage are reused.
