# RESORT OS — CURRENT STATE

Version: 5.0
Date: 2026-09-06
Status: RESORT OS 0.61.0 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Accepted release source PR: `#116` — `audit/full-project-fixes-20260905 -> main`.
Exact accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`.
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.
Post-merge truth reference: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.

Evidence:

- exact PR #116 head: **59/59 pull-request workflows SUCCESS, 0 failures**;
- accepted executable head and observed main merge have **0 changed files** between them;
- observed main merge triggered 40 push workflows: **38 product/security/migration/staging workflows SUCCESS**;
- `Release RC Truth CI` and `Launch Acceptance CI` failed closed on that merge because the previous frozen manifest still described 0.60.0; the 0.61.0 refreeze exists specifically to close that intentional release-truth gap without weakening the gates.

The machine-readable release manifest is `release/current-rc.json`.
Production source branch is `main`. Source selection does **not** authorize external deployment or DNS cutover.

## Architecture authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Core product surfaces:

- Public Next.js site;
- Resort OS Admin/PMS;
- Staff PWA for MAID / TECHNICIAN / DINING and controlled operational roles;
- Guest OS / Guest CRM;
- Kitchen / Dining operations;
- FastAPI Resort Core;
- PostgreSQL 16;
- n8n automation contracts.

`ReservationRequest != Reservation`.
OWNER/MANAGER retain reservation and payment authority. AI/n8n may create bounded requests and messages but may not confirm payment, guarantee a Reservation, invent payment policy, check in/out, refund, bypass Core pricing/availability or write generic business truth directly to PostgreSQL.

NFC acquiring/wallet remains outside active V1. Real bank/TTLock activation remains fail-closed until actual provider credentials/contracts/hardware E2E exist.

## Database release contract

The frozen 0.61.0 committed migration chain contains **22 migrations**:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`
9. `8_dining_service_control`
10. `9_guest_offer_campaigns`
11. `z10_service_point_paid_access`
12. `z11_owner_corrections_20260905`
13. `z12_guest_service_settings_20260905`
14. `z13_housekeeping_charges_20260905`
15. `z14_dining_entitlements_20260905`
16. `z15_group_bookings_20260905`
17. `z16_site_media_20260905`
18. `z17_dining_floor_layout_20260905`
19. `z18_site_media_slots_20260905`
20. `z19_dining_table_status_guard_20260905`
21. `z20_dining_active_table_unique_20260906`
22. `z21_dining_production_snapshots_20260906`

Shared release tooling fingerprints **87 critical domain constraints** through `scripts/release_contract.py`.
Production/staging migration mechanism is only `npx prisma migrate deploy`; do not use `prisma db push` for production migration.

Canonical property data remains:

- 84 rooms;
- 12 room categories;
- 48 rate rows.

Physical room intake is closed. Rooms 501/502 are canonically the owner-approved two-person basement inventory above the laundry; the stale mansard/single classification is no longer authoritative.

## Public site

Repository/CI verified:

- RU/KG/EN public truth;
- Transfer before Tours;
- Core availability/pricing;
- ReservationRequest creation boundary;
- no invented fixed prepayment percentage;
- no automatic Reservation/Payment confirmation;
- CMS published-only runtime;
- CMS Media Library Draft -> Publish flow;
- current approved contact/service facts;
- public room-media integrity guards.

Existing Vercel review deployments are review/demo surfaces, not proof that `3korony.com` production matches this RC.

## PMS / Reception

Current PMS includes:

- room x night chessboard;
- single-night and multi-night selection;
- Core pricing preview/commit;
- booking/move/resize/Split Stay flows;
- stale/conflict/race rejection;
- TECH_BLOCK protection;
- CLEAN check-in gate;
- realtime/audit;
- factual RoomAssignment relocation;
- checkout -> DIRTY -> housekeeping lifecycle;
- group booking;
- Guest OS PIN/session lifecycle;
- OWNER / MANAGER / RECEPTION / MAID / TECHNICIAN / DINING boundaries where defined.

0.61.0 audit corrections align guest folio UI with backend authority: OWNER/MANAGER retain payment recording/waive/void authority; RECEPTION can read finance and create allowed service charges without forbidden payment mutations.

Payment idempotency now includes normalized actual `paid_at` so the same idempotency key cannot silently replay a different payment timestamp.

## Stay / Guest OS / CRM

Implemented and regression-gated:

- `Stay` and `RoomAssignment` lifecycle;
- Room QR + 6-digit PIN + HttpOnly GuestSession;
- checkout session revocation;
- Guest OS requests;
- Guest CRM repeated-stay/relocation history;
- manager-confirmed preferences;
- GuestHistoryEvent and AuditLog trails;
- manager-controlled Guest Marketplace/offers;
- Kitchen menu/order access through GuestSession authority.

Room QR is **not** a physical lock credential. Anonymous Service Point QR is a separate context.

## Kitchen / Dining

Kitchen/Dining is Core/PostgreSQL-backed and does not create a parallel accounting truth.

Current release includes:

- Kitchen Admin and dining staff surfaces;
- editable RU/KG/EN menu;
- hotel-local daily menu publication by meal type;
- stop-list / restore;
- factual table register and visual Dining Floor;
- OWNER/MANAGER layout editing;
- table state/capacity/time-conflict protection;
- waiter assignment;
- Stay-linked Dining Sessions;
- order lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- Guest OS Kitchen orders;
- server-derived totals;
- Dining arrival cards;
- active-table uniqueness guard;
- Dining production snapshots with integrity constraints for meal/count/fingerprint/reason.

Kitchen/Dining operational amounts do not automatically become Hotel `Payment` or alter accommodation commercial truth.

## Housekeeping / Maintenance / Guest Services

Implemented and regression-gated:

- MAID / TECHNICIAN workflows;
- unified Guest Services Center over canonical OperationalTask;
- role-based routing;
- claim/complete/checklist/report flows;
- room readiness controls;
- anonymous Service Point QR -> OperationalTask;
- no hidden automatic payment effects.

0.61.0 changes missed 3-day housekeeping catch-up to `LATEST_DUE_ONLY`: downtime must not generate a burst of historical OPEN tasks. Included-linen and idempotency semantics remain preserved.

## Group bookings / folio / finance

Implemented:

- atomic group booking;
- guest folio charges separated from actual Payments;
- payment timestamp/idempotency corrections;
- remaining/overpaid/debt views including checked-out debt;
- Owner Intelligence / Control / Growth / Dashboard analytics.

Growth outbound authority remains `NONE_AUTOMATIC`.

## Service Point QR / physical access boundary

Service Point QR is implemented with opaque display-once tokens, rotate/revoke lifecycle, public routing and context-mixing protections.

A paid-access Core boundary exists, but **real bank acquiring and real TTLock actuation are not production-verified**. Do not treat static bank QR, client callback or repository mocks as proof of payment or door opening.

NFC acquiring/wallet remains deferred outside active V1.

## AI / n8n / messaging

Implemented contracts include:

- unified messaging inbox;
- provider idempotency and delivery evidence semantics;
- `Conversation <-> ReservationRequest` linkage;
- AI draft authority boundary;
- n8n -> Resort Core contract;
- Telegram sales contract;
- Staff Voice contract;
- owner-approved guest facts;
- fail-closed provider secret/config validation.

No provider is considered live merely because repository CI is green. Real provider E2E is external launch evidence.

## Production safety corrections in 0.61.0

- production/prod environment without `DATABASE_URL` fails closed instead of silently falling back to development storage;
- canonical room register guards prevent 501/502 owner corrections from drifting back through seed/import paths;
- workflow branch-truth guard requires canonical release workflows to cover `main`;
- payment and Reception finance authority are aligned across Core and UI;
- housekeeping catch-up avoids historical task bursts.

## Release governance

Repository facts:

- accepted executable head `e1ac7003abe7f63bd306778edd50a1c63dab6f17`: **59/59 PR workflows SUCCESS**;
- tree-equivalent main merge `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`: **0 changed files** vs accepted head;
- main merge: **38 successful non-refreeze workflows**, with two intentional pre-refreeze fail-closed release gates;
- release ledger: **22 migrations / 87 critical constraints / 84 rooms / 12 categories / 48 rates**.

Production governance remains fail-closed:

- GitHub `main` branch is currently `protected:false`; required-check enforcement is off — issue #91;
- Google Drive launch-control permissions remain NOT VERIFIED; latest audit recorded public writer exposure — issue #100;
- actual Beget/staging/rollback/device/provider/monitoring/backup/DNS evidence is incomplete;
- explicit final owner cutover approval has not been given.

## Deployment state

### GO — internal release engineering

Resort OS 0.61.0 is the intended refrozen internal external-production candidate once this release-hygiene PR itself is green and merged.

### STOP — external production cutover

External production remains **NOT VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP** until all required launch evidence is VERIFIED:

1. GitHub branch protection / required checks;
2. Google Drive launch-control permission remediation;
3. actual Beget host/account preflight;
4. verified rollback package for current live `3korony.com`;
5. isolated external HTTPS/WSS staging;
6. real staging room reconciliation;
7. external public-truth probe;
8. real-device acceptance;
9. provider E2E for every launch-enabled provider;
10. monitoring/alerting evidence;
11. fresh pre-cutover backup + off-site copy;
12. DNS rollback capture;
13. explicit owner GO.

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` and `scripts/verify_launch_acceptance.py`.
Canonical release manifest: `release/current-rc.json`.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not reactivate NFC or grant automatic commercial/payment authority as a side effect of deployment work.
