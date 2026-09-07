# Resort OS 0.62.1 — release acceptance record

Date: 2026-09-07  
Repository: `stvelikiy-star/resort-os`  
Accepted source PR: `#125` — `audit/internal-hardening-20260907 -> main`  
Accepted executable head: `b3bb0c1be4c522d765509796ddd1d32e8606dc89`  
Observed tree-equivalent main merge: `7f689458b2cf507d76a8c54fbe164e9492f79aca`  
Production source branch: `main`

Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

## Why 0.62.1 exists

0.62.1 is a controlled patch refreeze after strict internal management hardening. It does not add a new public-site feature set.

The hardening pass found and corrected two real management/security defects:

1. historical `/admin/demo` was a separate route that bypassed the normal AdminShell authentication path; it is now fail-closed to 404;
2. Kitchen `bootstrap-draft` remained callable by `DINING_STAFF`; it is now manager-owned and fail-closed in production.

The public website source remained frozen: PR #125 changed **zero files under `apps/web/**`**.

## Evidence

Accepted hardening head `b3bb0c1be4c522d765509796ddd1d32e8606dc89` completed **28/28 workflows SUCCESS, 0 failures**.

Observed main merge `7f689458b2cf507d76a8c54fbe164e9492f79aca` is tree-equivalent to that accepted executable head.

The observed merge completed **23/23 eligible product/security/migration/staging workflows SUCCESS**. One additional `Release RC Truth CI` run failed closed because the old 0.62.0 manifest correctly detected executable drift; this document and the 0.62.1 refreeze close that release-control gap.

The final post-merge Resort OS Release Gate completed successfully through clean PostgreSQL migration, canonical seed, OWNER bootstrap, Admin/Public/Staff builds, Core startup, Site/PMS/CMS smoke, full-domain E2E, Dining folio E2E, Chef production snapshot E2E, Dining coordination E2E and root control-center verification.

## Frozen property/database contract

- 22 committed migrations;
- 87 critical domain constraints;
- 84 physical rooms;
- 12 canonical room categories;
- 48 rate rows;
- rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

External migration uses `npx prisma migrate deploy`, not `prisma db push`.

## Authority boundaries

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.
OWNER/MANAGER retain reservation/payment authority.
AI/n8n cannot confirm payments or guarantee reservations.
Kitchen/Dining totals do not automatically create Hotel Payments.
Real bank/TTLock remain provider/hardware gated.
NFC acquiring/wallet remains outside active V1.

## External phase

Per owner plan, GitHub branch protection and Google Drive permission hardening are recommendations/deferred controls and are not blockers for this internal release. Beget/VPS is intentionally the final external phase.

External staging, legacy rollback, devices, providers, monitoring, fresh backup/restore/off-site copy and DNS evidence are not claimed here. Production cutover remains unauthorized until the final external phase is completed and explicit owner GO is recorded.

**EXTERNAL PRODUCTION CUTOVER STOP**
