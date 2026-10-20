# MARINA SMART — execution sequence, 2026-10-20

## Source reconciliation (do not deploy 2026-09-25 baseline blindly)
- Existing Railway project `MARINA SMART Pilot`: empty production environment.
- Railway `Three Crowns Full Test`: offline services; its PostgreSQL volume is not available for Marina reuse.
- PR #243 is based on old `marina-smart/live-base-20260925` and duplicates the already-safe `services/api/Dockerfile` in more recent MARINA branches. It must not be merged instead of the current candidate.
- Latest observed integration lines include `marina-smart/channel-csv-batches-20261016` and `marina-smart/channel-mappings-20261016`; they diverge. Do not assume one contains the other's latest changes.
- Last integrated candidate manifest: `release/marina-smart-current-candidate.json`; it explicitly sets `production_cutover_authorized=false`, `tenant_context_enabled=false`. Current mapping changes have their own unverified CI gate.
- Manual Booking.com / Airbnb / Ostrovok imports and normalized CSV are implemented in candidate code; direct provider API/channel automation **is not**.
- Keep the approved compact PMS chessboard and existing RBAC unchanged.

## Required ordered gates
1. Select a reviewed integration commit that incorporates approved channel changes without losing latest approved UI. Compare trees of mapping / CSV branches, reconcile and run all prescribed CI gates.
2. Verify approved deployment package with Docker build for API/web/admin/staff. The existing candidate `services/api/Dockerfile` already provides Uvicorn startup; use it in an isolated environment. Do not port `deploy/ak-bermet-test-api.Dockerfile` into the shared app.
3. Provision separate staging resources; never use Three Crowns PostgreSQL or customer backups. Avoid deploying to the pre-existing Railway production environment without an explicit staging/release decision. Check billing exposure before provisioning resources.
4. Run migrations through the documented controlled migration procedure on the new, empty staging DB. No automated application-start bootstrap, no payment/provider activation, no shared customer passwords.
5. Run `python scripts/marina_staging_readiness.py --api https://YOUR-STAGING-API` (optionally `--web`, `--admin`, `--staff`). Only safe GET requests are sent. A success does not prove authorization or business flows.
6. Run two-property authenticated login/read/write/role-denial acceptance on synthetic tenants plus isolation, booking concurrency, seasonal pricing, CSV preview/rollback, AI context, i18n, WSS, browser and staff workflows.
7. Verify actual-target snapshot -> isolated restore -> checksums, auditable rollback rehearsal, monitoring and documented operations.
8. Only after gates 1–7 succeed propose live rollout. Never flip `MARINA_TENANT_CONTEXT_ENABLED` solely based on disposable CI; ensure tenant-scoped every endpoint.
9. OTA direct integration requires official access, provider-specific mapping, authenticated ingestion, outbound changes and reconciliation; do not advertise automatic synchronization before provider E2E.

## Current evidence and blockers
- Source architecture: `stvelikiy-star/resort-os`.
- Tested PR #241 head 116c65a7aaf50352dc5baf58e52983847f055390 reported 29/29 success in candidate notes; this is not external target verification.
- `channel-mappings` working tree proposes migration 32; staging and cross-tenant tests remain required.
- Railway health in Three Crowns environment: offline; Marina Pilot: no services.
- No production, data, DNS or paid provider changes included in this PR.
