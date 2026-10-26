# MARINA SMART — current staging candidate

Date: 2026-10-26

## Candidate identity

- Repository: stvelikiy-star/resort-os
- PR: #244
- Branch: fix/marina-staging-preflight-20261020
- Application baseline: 9c2e01ac3c755ad4fc75d2c6dec822b817795927
- Verified manifest revision: 2e7b33c565932ebc710b459c37dcc57658eac221
- Candidate manifest: release/marina-smart-current-candidate.json
- Migration ledger: 37 migrations
- Critical constraints: 105 (scripts/release_contract.py)

## Observed CI evidence

All 68 PR workflow runs for the verified manifest revision completed successfully.
The full-stack job checked out PR merge e74d4e59c4f56ca708cffe2f23811da4bdcf2308.
Its tree d4c0f90c895365eaa653f647f19f7583fbb0f7e9 exactly matches the
verified manifest revision. This is PR integration evidence, not a standalone
deployment or authorization for later commits.

- Full-stack API/browser, booking/conflicts, seasonal boundary prices, staff
  grants/revocation, QR/PIN and guest history:
  https://github.com/stvelikiy-star/resort-os/actions/runs/40336820093
- Two-property authenticated isolation and full restore, 67 public tables with
  matching rows and constraints:
  https://github.com/stvelikiy-star/resort-os/actions/runs/40336819705
- Chessboard moves, stale snapshots, split/relocation, checkout and housekeeping:
  https://github.com/stvelikiy-star/resort-os/actions/runs/40336820783
- AK BERMET synthetic inventory, owner navigation and client/role cycle:
  https://github.com/stvelikiy-star/resort-os/actions/runs/40336820341

These runs test disposable synthetic data. They do not prove a live hotel,
official provider connectivity or a customer database backup.

## Customer isolation boundary

Tenant/Property remains the customer isolation model. Trusted tenant_id and
property_id come from database-derived authentication context. Verified
two-property restore tests use PROPERTY_PINNED_RUNTIMES: separate API processes
pinned to each property, sharing a disposable database. They do not prove a
single-API multi-hotel SaaS service. Tenant context remains disabled by default.

The existing roles, navigation and approved compact chessboard remain unchanged.

## What remains before public use

- external_staging_verified=false
- cross_tenant_e2e_verified=false (target deployment acceptance)
- backup_restore_target_verified=false
- production_cutover_authorized=false

Public demo access still requires a reachable HTTPS deployment and browser
acceptance on that deployment. The local Docker demo binds to localhost; it is
not a public demonstration URL. The historical Admin /demo route returns 404;
the local demo uses the authenticated existing Admin interface.

Live WhatsApp delivery, official OTA synchronization and acquiring are not
configured. Manual/CSV external bookings and offline provider tests must not
be described as live integrations. Payments and NFC remain disabled in the
candidate profile.

## Next actions

1. Validate every code change on the current PR head; retain the evidence above
   as a dated baseline, never as proof for subsequent untested changes.
2. Complete demo acceptance on an explicitly selected reachable environment.
3. Verify target migration ledger, backup/restore, HTTPS/WSS and rollback before
   a real hotel pilot.
4. Ubuntu remains untouched under the owner's current instruction. No new
   infrastructure, provider activation or production deployment is authorized
   by this document.
