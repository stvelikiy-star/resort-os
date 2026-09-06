# RESORT OS — CURRENT STATE

Version: 6.0  
Date: 2026-09-07  
Status: RESORT OS 0.62.0 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.
Accepted source PR: `#122`.
Accepted executable head: `609a309c97f30b5f95828956188507fc35ed3d0d`.
Observed tree-equivalent main merge: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`.
Production source branch: `main`.

Evidence:

- PR #122 accepted head: **21/21 workflows SUCCESS**;
- accepted head and main merge are tree-equivalent;
- main merge: **20 successful product/security/migration/staging workflows**;
- one `Release RC Truth CI` push failure was fail-closed release hygiene caused by the old 0.61.0 manifest; the 0.62.0 refreeze corrects it.

Machine authority: `release/current-rc.json`.

## Architecture authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.
OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee reservations, invent payment policy, check in/out, refund, bypass Core pricing/availability or write generic business truth directly to PostgreSQL.

Real bank/TTLock remains provider-gated. NFC acquiring/wallet remains outside active V1.

## Database/property release contract

Release 0.62.0 retains **22 committed migrations / 87 critical domain constraints**.
Canonical property baseline remains **84 rooms / 12 room categories / 48 rate rows**.
Rooms 501/502 remain owner-approved two-person basement rooms above the laundry.

Production/staging schema changes use `npx prisma migrate deploy`; never replace the committed ledger with `prisma db push`.

## Product state

Repository/CI verified product contour includes:

- public RU/KG/EN site, Core availability/pricing, CMS published-only runtime and ReservationRequest boundary;
- PMS supershakhmatka, rates/seasons, move/resize/Split Stay, stale/conflict protection and realtime;
- Reception, group booking, CLEAN check-in gate, Stay/RoomAssignment and checkout -> DIRTY -> housekeeping;
- OWNER/MANAGER/RECEPTION/MAID/TECHNICIAN/DINING RBAC where defined;
- Guest OS Room QR + PIN + HttpOnly session, requests, CRM history/preferences and manager-controlled offers;
- Guest Services unified task center;
- Operations assignment/history, inspection/rework and TECH_BLOCK protection;
- Kitchen/Dining production management: real menu item creation, draft/publish, price/publish authority for OWNER/MANAGER, operational DINING_STAFF access, stop-list, table/session/order lifecycle and production snapshots;
- finance/folio separation, payment idempotency, debt/remaining/overpaid views and owner analytics;
- Service Point QR privacy boundaries;
- Unified Inbox, Telegram, Staff Voice, AI and n8n authority contracts;
- backup/restore tooling, production package validation and final management acceptance.

PR #122 changed no public website source files; the public site remained frozen during final management closure.

## Final management acceptance

The accepted system includes the complete daily management menu: Dashboard, PMS, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Dining, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports, Content, Operations, Staff and Inbox.

`Management Final Acceptance CI` validates 70+ runtime/RBAC/CI invariants plus Core compile and Admin/Staff typecheck/build.

## Production safety boundaries

- PostgreSQL is private to deployment network.
- Production `DATABASE_URL` is fail-closed.
- Guest folio charges are separate from actual Payments.
- Kitchen/Dining totals do not automatically create Hotel Payment.
- Growth outbound authority remains `NONE_AUTOMATIC`.
- Room QR is not a TTLock credential.
- provider activation requires real credentials/contracts/hardware E2E.
- a green repository does not prove live external infrastructure.

## External blockers

Production cutover remains **EXTERNAL PRODUCTION CUTOVER STOP** until verified real evidence exists for:

1. GitHub `main` branch protection / required checks;
2. Google Drive launch-control permissions;
3. actual host/account/network preflight;
4. legacy `3korony.com` rollback package;
5. isolated external HTTPS/WSS staging;
6. real staging room reconciliation;
7. external public-truth acceptance;
8. real-device Staff/Kitchen/Admin acceptance;
9. provider E2E for enabled providers;
10. monitoring/alerting;
11. fresh backup + restore + off-site copy;
12. DNS rollback capture;
13. explicit owner GO.

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.
Canonical deployment procedure: `docs/DEPLOYMENT_RUNBOOK.md`.
Canonical release manifest: `release/current-rc.json`.

## Extension rule

Extend rather than rewrite the verified Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/Operations/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not reactivate NFC or grant automatic commercial/payment authority as a side effect of deployment work.
