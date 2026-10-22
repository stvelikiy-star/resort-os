# MARINA SMART — execution sequence for own Ubuntu host

Update: 2026-10-22. Railway is not the target infrastructure for this rollout. Use the AI PROF KG Ubuntu host and the owner's domain. References below to previous Railway resources are historical observations only; do not provision or deploy there.

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
2. Verify a MARINA-specific deployment package with Docker builds for API/web/admin/staff. `compose.marina-fleet.yaml` is synthetic-only and `compose.production.yaml` / `.env.production.example` currently target Three Crowns (`THREE_CROWNS`, `3korony.com`, `/srv/three-crowns`); do not use those defaults for MARINA. Do not port `deploy/ak-bermet-test-api.Dockerfile` into the shared app.
3. Use a dedicated isolated environment on the AI PROF KG Ubuntu host for synthetic staging; never use Three Crowns PostgreSQL or customer backups. Preserve existing n8n, control-center services, systemd units, and network tunnels. Do not expose hotel stacks publicly before TLS/proxy and role-access checks.
4. Run migrations through the documented controlled migration procedure on the new, empty staging DB. No automated application-start bootstrap, no payment/provider activation, no shared customer passwords.
5. Run `python scripts/marina_staging_readiness.py --api https://YOUR-STAGING-API` (optionally `--web`, `--admin`, `--staff`). Only safe GET requests are sent. A success does not prove authorization or business flows.
6. Run two-property authenticated login/read/write/role-denial acceptance on synthetic tenants plus isolation, booking concurrency, seasonal pricing, CSV preview/rollback, AI context, i18n, WSS, browser and staff workflows.
7. Verify actual-target snapshot -> isolated restore -> checksums, auditable rollback rehearsal, monitoring and documented operations.
8. Only after gates 1–7 succeed propose live rollout. Never flip `MARINA_TENANT_CONTEXT_ENABLED` solely based on disposable CI; ensure tenant-scoped every endpoint.
9. OTA direct integration requires official access, provider-specific mapping, authenticated ingestion, outbound changes and reconciliation; do not advertise automatic synchronization before provider E2E.

## Current evidence and blockers
- Source repository: `stvelikiy-star/resort-os`; PR #244 targets `marina-smart/channel-mappings-20261016` at `ded416371a62ab32167585ff9c8a92c729ef8a3c`.
- Current PR head at this update: `e7f3f94856e40201944f3e76386f030eae6744e8`; candidate source recorded in the manifest: `d7483660bff070556c060e9df0049d70749b7c65`.
- 65 GitHub Actions workflow runs returned for `e7f3f94`; all 65 have `success` conclusion. The `staging-full-gate` job is explicitly `skipped`; this is not external staging acceptance.
- MARINA two-property synthetic isolation/restore, full-stack synthetic smoke, Ubuntu fleet synthetic test, API image, AK BERMET CI, and public browser jobs passed.
- Local checks passed: 405 hardening checks, release contract (36 migrations / 105 critical constraints), 32 MARINA unit tests, Python compile, and `git diff --check`.
- The Ubuntu fleet Compose is a synthetic-only harness. No real-hotel production provisioning path or MARINA-specific public-domain deployment package has been verified.
- `scripts/provision_empty_marina_property.py` now provides a one-shot empty-property bootstrap for a dedicated `marina_…` PostgreSQL database. It requires explicit `APP_ENV`, confirmation, and a 16+ character initial-owner password from the operator's secret environment; refuses any database with rows in public application tables; and creates only tenant, property, empty direct rate plan, product settings, and one OWNER account. It creates no room, price, guest, reservation, payment, or test fixture. Disposable PostgreSQL CI verifies the password hash, signs in the owner through the API, checks the authenticated session, then adds synthetic fixtures and tests hotel API readiness and availability. It has not been run against any customer or Ubuntu database.
- Actual Ubuntu hardware/services, DNS, HTTPS/WSS, target database backup/restore, and rollback have not been observed from this workspace.
- Railway observations in the 2026-10-20 version of this runbook are historical and are not part of the chosen deployment plan.
- No production, real customer data, DNS, payment, or live provider changes were made.
