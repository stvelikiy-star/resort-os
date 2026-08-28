# Three Crowns Resort OS — Release Candidate Gate

Date: 2026-08-28

## Candidate

The current integration candidate preserves the core invariant:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Google Sheets and CMS are not parallel booking, inventory, or payment sources of truth.

Current fully audited code head:
`be6809381220444ff663bdf82aec65a0ea9b1e06`.

All 21 workflow contours associated with that audited head completed with conclusion `success`.

## Verified product / repository gates

- public site truth and multilingual booking boundaries;
- Admin/Web/Staff typecheck and production builds;
- Resort Core availability -> ReservationRequest -> manager payment -> Reservation -> PMS -> check-in -> checkout -> housekeeping;
- PMS schedule preview/commit, move, resize, Split Stay and history protection;
- authenticated realtime PMS WebSocket contract;
- housekeeping / maintenance lifecycle;
- unified inbox, Telegram sales and AI draft-only boundaries;
- payment idempotency;
- n8n and automation contracts;
- data-intake integrity: 84 rooms / 12 categories development baseline;
- 13 critical PostgreSQL invariants including active room-overlap exclusion;
- migration-aware PostgreSQL backup -> clean restore -> identical migration ledger;
- Control Center trusted-manifest fail-closed contract;
- dormant NFC exclusion from active runtime.

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

Current audited runs:
- Production Migration Baseline CI `33154426088` — success;
- PostgreSQL Backup Restore CI `33154426085` — success.

## Verified CI-local Docker staging gate

Workflow: `Three Crowns Full Staging Gate`.

Audited code head: `be6809381220444ff663bdf82aec65a0ea9b1e06`.

Successful GitHub Actions run: `33154426108`.

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

Status: **CI-LOCAL DOCKER STAGING VERIFIED**.

It is not equivalent to external HTTPS/WSS staging or production verification.

## Verified single-server production package

The approved production simplification is now a single VPS/VDS package:
- Caddy HTTPS/WSS edge;
- web/admin/staff Next.js;
- FastAPI Core;
- private PostgreSQL;
- n8n;
- persistent media/PostgreSQL/n8n state;
- local backup path with off-site copy expected.

Workflow: `Three Crowns Single Server Production Package CI`.

Successful run: `33154426092`.

Verified:
- production Compose graph;
- Caddy configuration;
- PostgreSQL not published on host port 5432;
- Admin WSS build wiring -> `wss://api.3korony.com`;
- production backup + non-destructive host-preflight script syntax;
- pinned `n8nio/n8n:2.36.2` image is pullable;
- deterministic API/web/admin/staff images build successfully.

Status: **SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / NOT EXTERNALLY DEPLOYED**.

## Dependency security / reproducibility

Current locked frontend runtime:
- Next `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- PostCSS override `8.5.23`.

Committed lockfiles exist for web/admin/staff and Docker builds use `npm ci`.

Dependency Security Inspection run `33154426079` completed successfully and recorded:
- info 0;
- low 0;
- moderate 0;
- high 0;
- critical 0;
- total 0.

The dependency workflow is read-only and no longer mutates the PR branch.

## Purchased hosting / legacy site truth

The production package is ready to be evaluated on the existing Three Crowns hosting, but the host itself is not yet proven suitable.

`scripts/host_preflight.sh` is a non-destructive host capability probe. It checks Linux/architecture, CPU/RAM/disk, root/sudo, Docker/Compose, registry reachability, 80/443/5432 listeners and target persistent-storage capability without stopping or installing anything.

The currently live legacy `3korony.com` must remain serving until:
1. its files/config/database (if any) have a recorded backup and checksum;
2. rollback is defined;
3. the new system is validated on staging/subdomains;
4. external acceptance is green.

## External staging truth

External HTTPS/WSS remains **NOT VERIFIED** because the actual purchased host has not yet been inspected or connected through the available tooling.

The next accepted topology is the purchased host itself if it passes preflight; no separate Replit/Vercel/Supabase production dependency is required by the chosen architecture.

Real external acceptance must prove:
- HTTPS/TLS;
- secure cookies;
- exact CORS behavior;
- PMS WSS upgrade;
- public/API/admin/staff routing;
- private PostgreSQL;
- real iPhone/Android/Telegram behavior.

## Still blocking production cutover

1. Purchased hosting must pass `scripts/host_preflight.sh` or be upgraded to a suitable VPS/VDS.
2. Current live `3korony.com` must have a verified backup/rollback point before replacement.
3. Owner-confirmed physical 84-room register; unresolved `OWNER_CHECKLIST` facts must not be guessed.
4. Complete external HTTPS/WSS staging acceptance on the actual host.
5. Real iPhone/Android/Telegram mobile acceptance.
6. Fresh production backup -> clean restore proof and final `production_preflight.py` immediately before cutover.
7. Production secrets / controlled DNS-apex cutover / documented rollback point.

No production merge or DNS switch is authorized by this document alone.
