# Resort OS 0.60.0 — release acceptance evidence

Date: 2026-09-05  
Property: Three Crowns / Три Короны, Cholpon-Ata, Kyrgyzstan  
Release branch: `feature/owner-corrections-20260905`  
Application version: `0.60.0`

## Acceptance state

The production-like branch release gate is GREEN for tested code commit:

- commit: `8364f67113edecb4d042906729af0d67d21332b3`
- GitHub Actions run: `33973604159`
- workflow: `Resort OS Release Gate`
- conclusion: `success`

This document records the tested release baseline. Merge/deployment to `main` remains a separate controlled action; the release gate is configured to run on `main` as well as feature branches and pull requests.

## What 0.60.0 closes

### CMS Media

- real image asset storage for JPEG / PNG / WebP;
- MIME and image-signature validation;
- byte-size limit, SHA-256 identity and deduplication;
- media library archive protection for published assets;
- independent media draft and published slot state;
- public site reads published media only;
- managed slots for Hero, conference, advantages, gallery and room categories;
- audit trail for media mutations.

### Dining Floor

- visual restaurant floor with normalized coordinates;
- zones and table shapes;
- OWNER / MANAGER drag-and-drop layout editing;
- staff read-only operational floor view;
- Stay-linked dining sessions;
- guest, room, party and waiter context on floor;
- kitchen order state visibility including READY;
- PostgreSQL invariant that prevents legacy Kitchen order transitions from releasing a table with an active Dining Session;
- Dining Session release, rather than food service completion, owns the transition to CLEANING.

### Group booking + folio integration

- atomic multi-room group reservation flow;
- guest folio separates receivable charges from actual Payments;
- kitchen order posting is idempotent and does not fabricate a payment;
- reservation payment timestamp handling is normalized as explicit UTC at API/audit boundaries and UTC-naive only at the Prisma/PostgreSQL `timestamp without time zone` storage boundary.

### Canonical hotel truth

- 84 physical rooms are preserved;
- 12 canonical categories are preserved;
- tariff-only category evidence is retained without inventing physical rooms after the owner-approved 501/502 correction;
- 48 tariff rows seed successfully;
- manager and reservation contact: `+996 558 08 50 02`;
- conference hall: confirmed, 20–120 guests, banquet use supported;
- guest fact version: `2026-09-05`;
- old two-day unpaid booking rule remains stale/do-not-use;
- launch payment providers remain fail-closed until verified.

## Production-like acceptance gate

Run `33973604159` passed all of the following on clean PostgreSQL 16:

1. Prisma schema validation.
2. `prisma migrate deploy` for every committed migration.
3. Prisma migration status verification.
4. Python compilation of Resort Core and scripts.
5. Verification of migrated Dining / Folio / Group / CMS Media tables, floor columns and Dining table status trigger.
6. Three Crowns seed: 84 rooms / 12 room categories / 48 rate rows.
7. OWNER bootstrap.
8. Admin TypeScript typecheck and production Next.js build.
9. Public Web TypeScript typecheck and production Next.js build.
10. Staff PWA TypeScript typecheck and production Next.js build.
11. Resort Core startup/readiness.
12. Existing unified Site / PMS / CRM / CMS smoke suite.
13. Owner-approved automation truth contract.
14. Release 0.60 full-domain E2E.
15. Root monorepo control-center verification.

## Full-domain E2E path

The release E2E verifies the connected business path rather than isolated endpoint existence:

`OWNER login → CMS media upload → media draft invisible publicly → publish → atomic group booking → folio receivable → actual internal payment fact → check-in → Stay → meal entitlement → chef production → Dining Floor table → Stay-linked seating → Kitchen order → folio posting → ACCEPTED → COOKING → READY → SERVED → occupied-table PostgreSQL guard → Dining Session RELEASED → table CLEANING`

## Defects discovered by the release gate and fixed

- duplicate `zoneLabel` migration drift between Dining migrations;
- duplicate application of baseline PostgreSQL constraints after `migrate deploy`;
- seed loss of `SINGLE_IMPROVED` after owner correction of rooms 501/502;
- invalid PostgreSQL `FOR UPDATE` on nullable outer-join sides in folio code;
- aware-vs-naive datetime bind failure for `payments.paidAt`;
- competing Kitchen vs Dining sources of truth for table availability;
- stale n8n guest-fact assertions for conference and manager contact;
- new Dining / Group / Chef flexbox compatibility warnings.

## Release rule going forward

A version must not be described as stable solely because it builds locally. The minimum release evidence is:

- clean-db committed migration deploy;
- seed integrity;
- all three production builds;
- Resort Core smoke;
- owner-approved automation truth;
- full-domain E2E;
- root monorepo verification.

`Resort OS Release Gate` now runs for feature branches, pull requests and `main`, so this acceptance rule remains executable rather than documentary only.
