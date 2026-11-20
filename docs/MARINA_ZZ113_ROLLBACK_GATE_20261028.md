# MARINA SMART — zz113 rollback rehearsal gate (staging only)

Status: **NOT YET EXECUTED ON UBUNTU**. This is a reviewed runbook candidate, not restore evidence.

## Pinned release boundary
- Staging Git commit: `f1b19d5e4844c391eb6abd614189d8f90794733a` (merged PR #262).
- Last observed Ubuntu checkout: `b69532337b7b2f3e04108f23912218038b818448`. This is **not** proof of the running Docker image SHA.
- Migration: `packages/database/prisma/migrations/zz113_marina_housekeeping_schedule_date_20261027/migration.sql`.
- Incident fixed: HTTP 500 from `/api/v1/ops/housekeeping/schedule/ensure`, caused by `operational_tasks_service_context_type_check` rejecting housekeeping `serviceCode/serviceDate`.
- Confirmed isolated Ubuntu rehearsal: restored 2026-10-27 dump into `marina_zz113_restore_test`; applied zz113; verified `scheduledFor`, unique index and checks; two matching inserts produced one row; transaction rolled back.

## Mandatory safety gate before staging deployment
1. Obtain **actual running** image digests, compose config and Git commit from the target host. Do not infer running images from git HEAD.
2. Verify current DB migration ledger ends at zz112 and audit existing `HOUSEKEEPING_SCHEDULE` rows. Stop if mismatch or unexpected rows.
3. Create a new `pg_dump -Fc` backup **outside containers**, with a restricted directory, timestamp, SHA-256 and `pg_restore --list` success. Secure an off-host copy.
4. Restore this exact backup to a **fresh isolated** database (not production); compare `_prisma_migrations` checksums and business-critical row counts. Do not count a prior restored database as a new rollback proof.
5. On **separate disposable targets**, rehearse: (a) pre-zz113 baseline; (b) zz113 with new API; (c) stop writers and **restore pre-zz113 dump to a clean database**; (d) verify the old API against restored schema and business data. Record evidence and timings, never credentials.
6. Verify business paths after upgrade: schedule ensure HTTP 200, second ensure no duplicate, concurrent ensures one task, intact guest service constraints, owner/staff authorization, cross-property isolation.
7. Rollback decision: if only application was updated and schema remained compatible, revert the pinned container images. Otherwise stop writes and restore the **entire database** from the verified pre-deploy backup; switch services only after contract checks pass. Never reverse zz113 by ad hoc `DROP COLUMN` against a live database.
8. Do not run Prisma `db push` in place of migration chain. No migrations or other writes on the running production database before above gate passes and authorized cutover.
9. After successful rehearsal, use versioned artifacts and run deployment preflight / health / smoke; keep the previous images and backup for rollback until acceptance signoff.

## Minimum recorded evidence
- Git/image digests (old/new), target DB identifier, migration ledger and constraint fingerprint.
- Backup file SHA256, full restore outcome, table count / migration hash comparison.
- Failed upgrade simulation and rollback test results, old API after restore.
- Real HTTP status + operation IDs for scheduling and staff creation; redact user identifiers and secrets.
- Explicit release go/no-go signed off, with remediation if any step fails.

## Current acceptance state
- GitHub unified PR #262: **46/46 workflows success** at head `3be019193b0417d085eaede9022fce903549f6a9`; merged into staging branch as `f1b19d5e4844c391eb6abd614189d8f90794733a`.
- Disposable zz113 test: PASS, but full application/database rollback: **NOT RUN**.
- Ubuntu staging deployment and real operational API: **NOT RUN**.
- Production cutover authorization: **NO**.
