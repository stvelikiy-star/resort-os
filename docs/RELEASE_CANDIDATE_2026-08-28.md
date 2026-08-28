# Three Crowns Resort OS — Release Candidate Gate

Date: 2026-08-28

## Candidate

The release candidate is the integration head that has passed the complete repository CI contour after committing the production migration baseline.

Core invariant:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Google Sheets and CMS are not parallel booking, inventory, or payment sources of truth.

## Verified gates

- public site truth and multilingual booking boundaries;
- admin/web/staff TypeScript typecheck and production builds;
- Resort Core availability -> request -> manager payment -> reservation -> PMS -> check-in -> checkout -> housekeeping;
- PMS chessboard schedule mutation preview/commit and history protection;
- authenticated realtime PMS WebSocket contract;
- housekeeping / maintenance operational lifecycle;
- unified inbox, Telegram sales and AI draft-only boundaries;
- payment idempotency;
- n8n and automation contracts;
- data intake integrity: 84 rooms / 12 categories baseline;
- committed Prisma `0_init` checksum and clean `migrate deploy`;
- 13 critical PostgreSQL invariants including active room overlap exclusion;
- migration-aware PostgreSQL backup -> clean restore -> identical migration ledger.

## Still blocking production cutover

1. Owner-confirmed physical 84-room register. The reconstructed intake remains fail-closed until the `OWNER_CHECKLIST` questions in Google Sheets are resolved.
2. External isolated HTTPS/WSS staging runtime for PostgreSQL + Core + web + admin + staff.
3. Full `staging_full_gate.py` against that deployed runtime.
4. Real iPhone/Android/Telegram mobile acceptance on staging.
5. Fresh production backup/restore proof and final `production_preflight.py` immediately before cutover.
6. Production secrets / DNS cutover / rollback point.

No production merge or DNS switch is authorized by this document alone.
