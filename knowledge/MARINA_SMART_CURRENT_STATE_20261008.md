# MARINA SMART — shared platform RC1 source candidate

Date: 2026-11-03, Asia/Bishkek.

## Candidate identity

- Repository: stvelikiy-star/resort-os
- PR: #284
- Branch: release/marina-shared-platform-rc1-20261103
- Application baseline: 59cdba4d098538c705998e32a924d9b5c62ed4b3
- Candidate manifest: release/marina-smart-current-candidate.json
- Migration ledger: 39 migrations
- Critical constraints: 106 (scripts/release_contract.py)
- Source stage: SOURCE_LOCKED_SHARED_RUNTIME_PENDING

The application baseline is the previously inspected source revision, not the
RC metadata commit. All 19 mandatory workflows must pass at the actual RC head.
Older runs and a successful source-lock check do not establish those results.
All 39 migration.sql files have exact SHA-256 checksums in the manifest.

## Previously verified baseline evidence

The baseline audit observed 29 successful PR workflow runs. Full-stack and
two-property jobs checked out merge aace18af2a6d6056c7e065a0eb8069d5d21d0ec1;
its tree equals baseline tree da1dd4d715da134dd7cd41ca94fd10c920177213.

- Full-stack booking, staff lifecycle, manual ledger, guest check-in/out and browser:
  https://github.com/stvelikiy-star/resort-os/actions/runs/41610201813
- Two-property HOLD, finance denial and restore of 68 public tables:
  https://github.com/stvelikiy-star/resort-os/actions/runs/41610201768

These are baseline results, not RC1 or Ubuntu approval. Manual payments are not
acquiring; provider-free assistant browser errors are not model answers.

## Customer isolation boundary

Tenant/Property remains the customer isolation model. Trusted tenant_id and
property_id come from database-derived authentication context. Two-property
checks currently use PROPERTY_PINNED_RUNTIMES, not the final shared backend.
The shared-auth preview still closes operational HTTP and WebSocket routes.

The existing roles, navigation and approved compact chessboard remain unchanged.

## Unverified rollout boundary

- external_staging_verified=false
- cross_tenant_e2e_verified=false
- backup_restore_target_verified=false
- production_cutover_authorized=false

MARINA_DEMO is the public synthetic demo. MARINA_HOTEL01 is the older separate
test stack, not the primary production platform. Existing data and deployment
settings are preserved. No Ubuntu commands, seed, migrations, DNS, real WhatsApp,
OTA or acquiring are executed by this source change.

## Next stages

1. Accept all mandatory RC1 source gates at one head.
2. Complete shared operational tenancy, onboarding and scoped background work.
3. Accept PMS, supported roles and restore/rollback on the unified source.
4. Inspect Ubuntu and prove restoration of a real backup into a separate DB.
5. Deploy the separate primary environment with permanent HTTPS; verify restart.
6. Accept real hotel-specific WhatsApp/AI delivery and handoff.
7. Accept a controlled real-property pilot.
8. Accept official OTA/acquiring integrations before advertising them.
