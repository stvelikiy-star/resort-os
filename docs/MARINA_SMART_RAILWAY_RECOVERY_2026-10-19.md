# MARINA SMART — isolated Railway recovery (2026-10-19)

## Evidence
- GitHub source: `stvelikiy-star/resort-os`, MARINA branch `marina-smart/live-base-20260925`.
- `MARINA SMART Pilot` Railway project has no services.
- `Three Crowns Full Test` has offline web/admin/staff/api/postgres; `postgres-data` volume must not be deleted or reused.
- Failed API deploy from 2026-09-28 shows Railpack "No start command detected", despite configured Dockerfile.
- Previously configured API Dockerfile `deploy/ak-bermet-test-api.Dockerfile` runs Ak-Bermet bootstrap and DB migrations on startup; unsafe as a generic MARINA deployment.

## Safe fix provided
- `deploy/marina-smart-api.Dockerfile` adds a dedicated API image with an explicit FastAPI command.
- Image deliberately does not apply migrations, run any hotel bootstrap, seed an object or touch third-party credentials.
- No existing Railway project, Docker service, database or property configuration has been changed.

## Release gates (all required before deployment)
1. Identify and freeze the accepted MARINA product SHA, confirm that this feature branch contains that exact approved UI/workflow.
2. Build isolated API image with repo-root Docker context and the new Dockerfile; verify import/start and `/health/live`.
3. Provision a **new, empty** PostgreSQL database in MARINA Pilot, not the Three Crowns volume.
4. Inspect DB migrations and `PROPERTY_CODE`; execute approved migrations explicitly, outside application startup.
5. Set secrets using Railway secret storage; prohibit demo credentials and cross-property access.
6. Verify `/health/ready`, auth, role isolation, seasons/prices, double-booking concurrency, staff workflows, MARINA AI.
7. Only after tests, attach public web/admin/staff; verify HTTPS/WSS and backup/restore; preserve rollback plan.
8. Never deploy onto Three Crowns production or share its PostgreSQL volume.

## Railway API service settings (proposed, NOT applied)
- Source: `stvelikiy-star/resort-os`, approved MARINA revision.
- Root directory: `/` (repository root).
- Builder: Dockerfile.
- Dockerfile path: `/deploy/marina-smart-api.Dockerfile`.
- Healthcheck: `/health/live` for liveness; separately verify `/health/ready` with provisioned DB.
- Expected listen port: 8000.

## Open questions to resolve through evidence
- Confirm latest accepted MARINA source SHA (not just branch name).
- Confirm API requirements/imports against built image.
- Confirm migration/seed scope for the chosen property; Three Crowns README is not universal MARINA scope.
- Verify cost and running state before enabling Railway deployments.
