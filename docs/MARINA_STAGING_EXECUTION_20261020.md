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
- The 2026-10-22 snapshot below supersedes this earlier head and CI count. The candidate source recorded in the release manifest remains `d7483660bff070556c060e9df0049d70749b7c65`; packaging changes do not authorize cutover.
- `scripts/provision_empty_marina_property.py` now provides a one-shot empty-property bootstrap for a dedicated `marina_…` PostgreSQL database. It requires explicit `APP_ENV`, confirmation, and a 16+ character initial-owner password from the operator's secret environment; refuses any database with rows in public application tables; and creates only tenant, property, empty direct rate plan, product settings, and one OWNER account. It creates no room, price, guest, reservation, payment, or test fixture. Disposable PostgreSQL CI verifies the password hash, signs in the owner through the API, checks the authenticated session, then adds synthetic fixtures and tests hotel API readiness and availability. It has not been run against any customer or Ubuntu database.
- Actual Ubuntu hardware/services, DNS, HTTPS/WSS, target database backup/restore, and rollback have not been observed from this workspace.
- Railway observations in the 2026-10-20 version of this runbook are historical and are not part of the chosen deployment plan.
- No production, real customer data, DNS, payment, or live provider changes were made.

## Verified package update — 2026-10-22

- PR #244 head: `73a9bf06167507adf808eb71f1e2ff905ec870b1`. All 66 GitHub Actions workflows on that exact commit completed successfully; no failures or pending runs. This includes MARINA isolated PostgreSQL API smoke, full-stack synthetic smoke, Ubuntu hotel fleet CI, and the MARINA Ubuntu production package CI.
- The Ubuntu package CI passed fail-closed environment/bootstrap tests, default and opt-in bootstrap Compose validation, strict Caddy config validation, provisioner image build, and package boundary checks. The isolated PostgreSQL smoke created a disposable empty property and OWNER account, verified login/session, then exercised synthetic availability.
- `compose.marina-production.yaml`, `.env.marina-production.example`, `deploy/marina/Caddyfile`, the one-shot `scripts/provision_empty_marina_property.py`, and `docs/MARINA_UBUNTU_PRODUCTION_RUNBOOK.md` now form a MARINA-specific Ubuntu deployment package. It is code- and CI-verified only. The provisioner refuses non-empty app databases and requires explicit operator confirmation plus a strong initial OWNER password.
- No real Ubuntu host, DNS, public HTTPS/WSS, customer data, production database, provider credentials, payments, or live backups were accessed. Actual-host preflight, browser/role acceptance, backup/restore, and rollback remain required before a pilot.
- The `staging-full-gate` remains skipped; these CI results are not external staging acceptance or production authorization. The release manifest still has `production_cutover_authorized=false` and `external_staging_verified=false`.
