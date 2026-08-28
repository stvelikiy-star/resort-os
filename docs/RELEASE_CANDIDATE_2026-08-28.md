# Three Crowns Resort OS — Release Candidate Gate

Date: 2026-08-28

## Candidate

The current integration candidate preserves the core invariant:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Google Sheets and CMS are not parallel booking, inventory, or payment sources of truth.

## Verified repository / CI gates

- public site truth and multilingual booking boundaries;
- admin/web/staff TypeScript typecheck and production builds;
- Resort Core availability -> request -> manager payment -> reservation -> PMS -> check-in -> checkout -> housekeeping;
- PMS schedule preview/commit, move, resize, Split Stay and history protection;
- authenticated realtime PMS WebSocket contract;
- housekeeping / maintenance lifecycle;
- unified inbox, Telegram sales and AI draft-only boundaries;
- payment idempotency;
- n8n and automation contracts;
- data-intake integrity: 84 rooms / 12 categories development baseline;
- 13 critical PostgreSQL invariants including active room-overlap exclusion;
- migration-aware PostgreSQL backup -> clean restore -> identical migration ledger.

## Verified production-like migration chain

Current committed migration chain:
- `0_init`;
- `1_site_content`.

`1_site_content` was added as a forward migration after the production-like staging gate exposed that CMS storage had previously been supplied outside the committed Prisma migration history. The baseline migration was not rewritten.

Verified:
- clean `prisma migrate deploy`;
- exact migration ledger `0_init,1_site_content`;
- `site_content_documents` present after migration;
- 84/12 seed;
- 13 critical database constraints;
- backup/restore with the complete migration ledger.

## Verified CI-local Docker staging gate

Workflow: `Three Crowns Full Staging Gate`.

Verified code head: `9b5c21293704a8573a904c2bf25221348a21a9bd`.

Successful GitHub Actions run: `33142971361`.

The gate starts a clean isolated topology and verifies:
- PostgreSQL;
- FastAPI Resort Core;
- public web;
- PMS admin;
- Staff PWA;
- synthetic OWNER/MAID/TECHNICIAN users;
- clean committed migrations;
- release/public/i18n guards;
- substantial real frontend application surfaces rather than simple preview stubs;
- complete `staging_full_gate.py` acceptance;
- active OpenAPI contains no NFC/beach routes;
- clean teardown.

This status is **CI-LOCAL DOCKER STAGING VERIFIED**.

It is not equivalent to external HTTPS/WSS staging or production verification.

## External staging truth

The connected Vercel project currently exposes only a simple preview/stub and is not accepted as Resort OS staging evidence.

The required external staging topology needs a host capable of running PostgreSQL + persistent FastAPI/WebSocket + web/admin/staff with real HTTPS/WSS, cookie/CORS configuration and mobile access.

No suitable connected container/VPS staging host is currently available through project tooling, so external staging remains BLOCKED rather than guessed or substituted.

## Still blocking production cutover

1. Owner-confirmed physical 84-room register. Reconstructed intake remains fail-closed until unresolved `OWNER_CHECKLIST` facts are confirmed.
2. External isolated HTTPS/WSS staging runtime for PostgreSQL + Core + web + admin + staff.
3. Complete gate against that externally deployed runtime, including TLS/cookie/CORS/WebSocket behavior.
4. Real iPhone/Android/Telegram mobile acceptance on staging.
5. Fresh production backup/restore proof and final `production_preflight.py` immediately before cutover.
6. Production secrets / DNS cutover / documented rollback point.

No production merge or DNS switch is authorized by this document alone.
