# API gap register — 15 November 2026

Current source inventory: [ROLE_SCREEN_MATRIX.md](ROLE_SCREEN_MATRIX.md). Baseline #516: `48ae43d3cb2028d5c71e105b264ff6372f19ae1f`. The former snapshot `34d705d2` is historical and must not be used to describe current implementation.

| Priority | Confirmed issue | Required resolution / evidence |
|---|---|---|
| P0 | AGENT service UI calls an endpoint whose baseline role dependency excludes ordinary AGENT | This branch narrows POST permission to PMS-enabled ACTIVE linked agents and their own reservation; keep GET queue denied, including custom SERVICES grants. Verify real PostgreSQL persistence and denial cases in Guest Services CI. |
| P0 | AGENT can add services only before leaving new-booking result | This branch reuses the durable service panel in the own-reservation PMS preview. Backend remains authoritative on deep-link/tampered IDs. |
| P0 | AGENT has no own service-status readback/date/time/note UI | Add scoped read contract and matching UI only after write security/persistence passes. Current ambiguous outcomes stay journaled and require manager reconciliation. |
| P0 | OWNER reports record movements but do not recognize revenue/expenses for profit | Define and implement accrual periods, refunds, service delivery and inventory cost attribution; never rename received-payments difference to profit. |
| P0 | Role inventory was stale (STORE blocked despite implementation, kitchen/finance omitted; DINING_STAFF absent) | Replaced with source operation inventory. Physical acceptance remains open. |
| P0 | Wider Web operations not all available on mobile | See each explicit role gap in the inventory; prioritize operational roles, retain existing functionality. |
| P0 | Single candidate runtime and database evidence incomplete | Re-run Mobile/Web/API/PostgreSQL checks on the final integration SHA after functional fixes. |
| Final | Expo Go / physical Android not yet verified | Device execution, network/restart/revocation and visual acceptance on final candidate. APK build is not device acceptance. |

No new hotel picker, no deployment to Ubuntu/Aska Tash, no AI or WhatsApp activation. Existing endpoints and canonical OperationalTask storage are reused.
