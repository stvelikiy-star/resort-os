# MARINA SMART shared platform RC1

Status: source preparation; not deployed or approved for production.
PR: https://github.com/stvelikiy-star/resort-os/pull/284
Branch: `release/marina-shared-platform-rc1-20261103`.
Reviewed application baseline: `59cdba4d098538c705998e32a924d9b5c62ed4b3`.

## Stage 1 acceptance

`release/marina-smart-current-candidate.json` is the single source-candidate
record. It retains the explicit false deployment/restore/shared-acceptance flags.
The application baseline is a reviewed source anchor; the actual RC head must
be named separately when reporting its CI. A metadata commit cannot contain its
own final Git SHA, and must not present its parent as a tested deployment.

All 39 migration.sql files, including zz114, are locked by SHA-256. The guard
rejects SQL drift, missing/extra migrations and missing/duplicate release gates.
All 19 mandatory workflows include the manifest in their pull_request paths.
Changing the manifest schedules their tests together, including shared-auth,
HOLD migration/rollback, staff, PMS, WhatsApp source contracts and image build.

The new offline gate runs all MARINA unit/contract tests with pinned API
dependencies. It is one required workflow, not a substitute for PostgreSQL,
browser, migration or Docker-image workflows.

Report every mandatory workflow at the same candidate head as PASS, FAIL,
PENDING, CANCELLED, SKIPPED or MISSING. Only PASS closes a required source gate.
Do not sum unrelated workflows or reuse older runs as acceptance of a new head.
The source check does not alter GitHub branch-protection settings or grant
production authorization.

## Stage 2 boundary

The shared-auth preview is still authentication only. Complete and test the
shared workspaces before opening their routes. Required coverage includes two
hotels with matching usernames, foreign resource IDs and forged headers,
disabled tenants, staff revocation, onboarding, guest/service flows, background
workers and provider secrets. Validate both allowed operations and denied
cross-property access in the intended shared topology.

The candidate contains the reviewed HOLD, booking, finance and hotel-setup
tenant-boundary changes. No application, mobile, demo, Ubuntu or customer DB
changes are part of stage 1. Re-pin the reviewed source and migration checksums
when stage 2 intentionally changes the application. Run the mandatory set again.
