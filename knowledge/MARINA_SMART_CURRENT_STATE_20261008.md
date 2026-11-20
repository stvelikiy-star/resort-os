# MARINA SMART — unified shared-platform RC2 source candidate

Date: 2026-11-04, Asia/Bishkek.

## Candidate identity — source review, NOT production

- Repository: stvelikiy-star/resort-os
- PR: #314
- Branch: release/marina-shared-platform-rc2-20261104
- Application baseline: 62a2caec856e8fe32801c9156d90de655298ad33
- Previous reviewed RC1: draft PR #284, head 488fec8b9823c6f98d690333dcc7c9b28fa86bc8
- Candidate manifest: release/marina-smart-current-candidate.json
- Migration ledger: 39 migrations
- Critical constraints: 106 (scripts/release_contract.py)
- Source stage: SOURCE_LOCKED_SHARED_RUNTIME_PENDING
- Scope: shared Tenant/Property platform; tenant_id and property_id must come from authenticated database-backed context

The baseline is the already-reviewed *application code* SHA, not the metadata head.
The RC2 branch is 92 commits ahead of RC1 and changes only 29 paths relative
to the frozen RC1. The main branch has independently diverged; a direct
main merge/force-push is forbidden until separately reconciled.
Existing draft PRs #303–#312 form a reviewed stacked source history.
Do NOT independently deploy or cherry-pick them into production.

## Observed synthetic CI evidence for application baseline

- Actual Chromium -> Next.js -> canonical FastAPI -> disposable PostgreSQL 16,
  two different hotels: booking and rates, HOLD/release, schedule mutation,
  unpaid cancellation, **manual staff-recorded** payment, guest check-in/one-time
  PIN, early check-out, revoked access and housekeeping:
  https://github.com/stvelikiy-star/resort-os/actions/runs/41711228040
- Resort OS Release Gate:
  https://github.com/stvelikiy-star/resort-os/actions/runs/41711228001
- On baseline PR #312 SHA, 20 of 21 reported runs were successful.
  The failure was 'Three Crowns Full Staging Gate' (public-content truth drift).
  This does not constitute success for all **19 required MARINA workflows**.
- RC2 requires those same 19 mandatory named workflows PLUS
  marina-shared-live-browser-postgres-ci.yml as an additional acceptance gate,
  all PASS at the **exact final RC2 metadata head SHA**. Older runs are not evidence.
- The SHA-256 manifest fingerprints exactly 39 migration.sql files including
  zz114. They do not prove migration or restore on any target server.

## Tenant isolation and role boundary

Tenant/Property is the customer boundary. The RC2 synthetic two-hotel run
uses one shared API/backend and verifies two distinct authenticated hotel
contexts for the tested PMS operations. This is stronger than the historical
PROPERTY_PINNED_RUNTIMES baseline but is NOT an accepted external shared service.

The existing roles, navigation and approved compact chessboard remain unchanged.
This sentence applies to the **legacy single-property UI**; RC2 adds a separate
shared-auth-preview staging cabinet containing a subset of dashboard, grid,
reservations, booking/HOLD and staff-management functionality.
It has NO complete operational workspaces for MAID/TECHNICIAN/COOK/WAITER, no
activated shared guest QR/service flow, and no accepted hotel onboarding.

Internal manual receipts are not connected acquiring or proof of money received.
The historical GREEN-API setup is property-pinned and deliberately rejects
tenant-context mode; production per-hotel WhatsApp and AI handoff remain unverified.

## Explicit unverified rollout boundary

- external_staging_verified=false
- cross_tenant_e2e_verified=false (target/external; synthetic E2E is evidenced above)
- backup_restore_target_verified=false
- production_cutover_authorized=false

MARINA_DEMO is an independent public synthetic demo. MARINA_HOTEL01 is an
older isolated hotel01 test stack, not the primary MARINA production runtime.
No changes to DEMO, hotel01 data, mobile, KÖL, AK BERMET, Ubuntu, deployment,
DNS, provider secrets or working databases are authorized by this candidate.

## Next ordered stages (NO-GO remains)

1. Get exactly 19 core + 1 real-browser RC2 checks green on one final SHA.
2. Accept unified PMS externally; complete all role cabinets/tasks and guest QR.
3. Validate new property/owner onboarding and tenant isolation.
4. Accept per-hotel real WhatsApp/AI/human handoff.
5. Run full release safety and migration/restore/rollback gates.
6. Inspect Ubuntu and deploy separately only after acceptance and recovery proof.

This document and manifest record a source review, NOT a deployment.
