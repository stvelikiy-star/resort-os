# RESORT OS — CURRENT STATE

Version: 4.0
Date: 2026-09-05
Status: RESORT OS 0.60.0 MERGED TO MAIN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Release PR: `#112` — `feature/owner-corrections-20260905 -> main`.
Exact tested PR head: `c8db446d367284465853850136c31274c8e39370`.
Main merge commit: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`.

PR #112 completed **46/46 checks successfully, 0 failures** on the exact tested head before merge. The PR was merged with an expected-head SHA guard, so GitHub would have rejected the merge if the head moved.

After merge, the resulting `main` commit completed **35/35 triggered main checks successfully, 0 failures**.

The repository release baseline is therefore merged and regression-green. This is still **not evidence of an external Beget/staging/production deployment**.

## Architecture authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Core product surfaces:

- Public Next.js site;
- Resort OS Admin/PMS;
- Staff PWA including MAID / TECHNICIAN / DINING flows;
- Guest OS / Guest CRM contracts;
- Kitchen / Dining operations;
- FastAPI Resort Core;
- PostgreSQL 16;
- n8n automation contracts.

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee a Reservation, invent a fixed prepayment percentage/payment route or bypass Core availability/pricing.

NFC acquiring/wallet remains deferred and outside active V1 composition.

## Database release contract

The current committed migration chain contains **20 migrations**:

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

Shared release tooling currently fingerprints **81 critical domain constraints** through `scripts/release_contract.py`.

Production/staging migration mechanism is only:

```bash
npx prisma migrate deploy
```

Do **not** use `prisma db push` for production migration.

A clean PostgreSQL 16 acceptance run successfully applied all 20 committed migrations and seeded the canonical property dataset:

- 84 rooms;
- 12 room categories;
- 48 rate rows.

The room intake/import gate remains closed at this canonical register. Do not collect the room register again.

## Public site

Repository/CI verified:

- RU/KG/EN public truth;
- Transfer before Tours;
- Core availability/pricing;
- ReservationRequest creation boundary;
- no fixed 30% prepayment claim;
- no automatic Reservation/Payment confirmation;
- CMS published-only runtime;
- CMS Media Library Draft -> Publish flow;
- current approved contact/service facts.

External rendered production truth is not yet verified on a real target host.

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
- checkout -> DIRTY/housekeeping lifecycle;
- Reception authority boundaries;
- Guest OS PIN/session lifecycle;
- OWNER / MANAGER / RECEPTION / MAID / TECHNICIAN / DINING access boundaries where defined.

The canonical room register is 84 rooms / 12 categories.

## Stay / Guest OS / CRM

Implemented and regression-gated:

- `Stay` and `RoomAssignment` lifecycle;
- Room QR and GuestSession/PIN access;
- checkout session revocation;
- Guest OS requests;
- Guest CRM history across repeated stays and relocations;
- manager-confirmed preferences;
- GuestHistoryEvent and AuditLog trails;
- Guest Marketplace / manager-controlled offers;
- Kitchen menu/order access through GuestSession authority;
- request flows that do not create payment/commercial truth automatically.

Room QR / GuestSession remains separate from anonymous Service Point QR.

## Kitchen / Dining

Kitchen is a Resort Core/PostgreSQL operational domain, not a parallel accounting system.

Current release includes:

- Kitchen Admin and dining staff surfaces;
- editable RU/KG/EN menu;
- hotel-local daily menu publication by meal type;
- stop-list / restore;
- factual table register;
- visual Dining Floor with OWNER/MANAGER layout editing and staff operational view;
- table states and capacity/time conflict guards;
- waiter assignment;
- Dining Sessions linked to Stay;
- Kitchen order lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- Guest OS Kitchen orders;
- server-derived totals;
- Dining arrival cards;
- table/session status invariants;
- Kitchen totals isolated from accommodation `Payment` and `Reservation.totalKgs`.

## Group bookings / folio / finance

Release 0.60 adds and verifies:

- atomic group booking flow;
- guest folio charges separated from actual Payments;
- corrected payment timestamps;
- PostgreSQL locking corrections found by production-like E2E;
- remaining/overpaid/debt views including checked-out debt;
- Owner Intelligence / Control / Growth / Dashboard analytics.

Growth outbound authority remains `NONE_AUTOMATIC`.

## Staff / Guest Services

Implemented and regression-gated:

- MAID / TECHNICIAN workflows;
- Dining staff operations;
- unified Guest Services Center over canonical OperationalTask;
- role-based request routing;
- staff voice contract;
- anonymous Service Point QR -> OperationalTask routing;
- no hidden automatic payment side effects.

## Service Point QR / NFC boundary

Service Point QR is implemented and CI-verified with opaque display-once tokens, rotate/revoke lifecycle, public routing and context-mixing protections.

NFC payment/acquiring remains outside the active V1 release boundary. A successful NFC boundary check verifies that it has not been accidentally reactivated.

## AI / n8n / messaging

Implemented contracts include:

- unified messaging inbox;
- provider idempotency and delivery evidence;
- `Conversation <-> ReservationRequest` linkage;
- AI draft authority boundary;
- n8n -> Resort Core contract;
- Telegram sales contract;
- Staff Voice contract;
- owner-approved guest facts and fail-closed provider configuration validation.

No provider is considered live merely because repository validation is green. Real provider E2E is external launch evidence.

## Release governance

Repository result:

- PR #112 exact tested head: **46/46 SUCCESS**;
- merged `main` commit: **35/35 SUCCESS**;
- main SHA: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`.

However, production governance remains fail-closed:

- GitHub `main` branch is currently observed as **not protected** and required-check enforcement is off;
- the frozen machine-readable RC manifest still represents the earlier explicitly frozen external-production candidate and has **not** been refrozen to the new main merge;
- external Beget/staging/rollback/device/provider/monitoring/backup/DNS evidence is still incomplete;
- explicit final owner cutover approval has not been given.

Therefore `main` being green does **not** authorize DNS switch or external production declaration.

## Deployment state

### GO — repository release engineering

Resort OS 0.60.0 is merged to `main` and current triggered repository checks are green.

### STOP — external production cutover

External production remains **NOT VERIFIED / CUTOVER STOP** until the launch evidence gate is closed, including:

1. GitHub branch protection / required checks;
2. Google Drive launch-control permission remediation/verification;
3. actual Beget host/account preflight;
4. verified legacy rollback package;
5. isolated external HTTPS/WSS staging;
6. public truth probe;
7. real device acceptance;
8. provider E2E for providers enabled at launch;
9. monitoring/alerting evidence;
10. fresh pre-cutover DB backup and off-site copy;
11. DNS rollback capture;
12. deliberate RC refreeze to the exact accepted release boundary;
13. explicit owner cutover approval.

## Launch rule

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` and `scripts/verify_launch_acceptance.py`.
Canonical frozen external-production manifest: `release/current-rc.json`.

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until every required external/governance evidence gate is VERIFIED.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not reactivate NFC or automatic commercial/payment authority as a side effect of deployment work.
