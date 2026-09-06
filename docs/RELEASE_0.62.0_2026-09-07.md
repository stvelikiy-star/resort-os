# Resort OS 0.62.0 — release acceptance record

Date: 2026-09-07  
Status: **INTERNAL RC FROZEN / REPOSITORY VERIFIED / EXTERNAL CUTOVER STOP**

Repository: `stvelikiy-star/resort-os`  
Accepted source PR: `#122` — `chore/management-final-acceptance-20260906 -> main`  
Accepted executable head: `609a309c97f30b5f95828956188507fc35ed3d0d`  
Observed tree-equivalent main merge: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`  
Production source branch: `main`

## Evidence

- accepted PR #122 head: **21/21 GitHub workflows SUCCESS, 0 failures**;
- accepted head and observed main merge use the same tree;
- observed merge: **20 eligible product/security/migration/staging workflows SUCCESS**;
- the only failed merge-push workflow was `Release RC Truth CI`, which failed closed because `release/current-rc.json` still described 0.61.0 before this refreeze;
- release 0.62.0 intentionally updates only release/control documentation and release truth after the accepted final product head.

## What 0.62.0 freezes

0.62.0 includes the final accepted management contour after the Kitchen/Dining production-management completion and Management Final Acceptance:

- PMS/supershakhmatka, rates/seasons, Reception, CRM, group booking;
- Guest Services, Guest OS, Guest CRM and manager-controlled offers;
- MAID/TECHNICIAN operations, inspection/rework and TECH_BLOCK protection;
- Kitchen/Dining real menu creation, draft/publish, OWNER/MANAGER menu authority, DINING_STAFF operational authority, tables/sessions/orders and production snapshots;
- finance/folio/payment-idempotency and owner analytics;
- Room/Service Point QR boundaries;
- Unified Inbox, Telegram/AI/n8n contracts;
- backup/restore, production package, full staging and release gates;
- final management acceptance with 70+ runtime/RBAC/CI invariants.

The public website source remained frozen during the final management acceptance PR.

## Database/property contract

Release 0.62.0 retains **22 committed migrations / 87 critical constraints** and canonical seed **84 rooms / 12 categories / 48 rate rows**.

External staging/production migration uses `npx prisma migrate deploy`. `prisma db push` is not production release evidence.

## Authority boundary

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. Kitchen/Dining totals do not automatically create Hotel Payment. Real bank/TTLock remains provider-gated. NFC acquiring remains outside active V1.

## External state

Repository acceptance does not prove the real host, real HTTPS/WSS, real devices, real provider delivery, real monitoring, Drive permissions, branch protection, backups, rollback or DNS state.

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until `knowledge/09_LAUNCH_ACCEPTANCE.md` is satisfied and explicit owner GO is given.
