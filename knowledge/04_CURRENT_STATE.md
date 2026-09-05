# RESORT OS — CURRENT STATE

Version: 4.1
Date: 2026-09-05
Status: RESORT OS 0.60.0 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`.
Release PR: `#112` — `feature/owner-corrections-20260905 -> main`.
Exact accepted executable head: `c8db446d367284465853850136c31274c8e39370`.
Observed tree-equivalent main merge: `e5efe074abb4a277c032b017ae5fb02c5d0d5039`.
Post-merge truth-only main head: `00fdb8d1b583cf418e1c39709fb79ca248e462e4`.

Evidence:

- PR #112 exact tested head: **46/46 checks SUCCESS, 0 failures**;
- accepted executable head and observed main merge have **0 changed files** between them;
- observed main merge: **35/35 triggered checks SUCCESS, 0 failures**;
- post-merge truth-only head: **4/4 triggered checks SUCCESS, 0 failures**;
- the post-merge truth delta changed canonical documentation only.

The machine-readable release manifest `release/current-rc.json` is deliberately refrozen to Resort OS `0.60.0` and the exact accepted executable boundary above.

The production source branch is now `main` because the accepted executable release is merged there. This does **not** authorize external deployment or DNS cutover while governance and real-world launch evidence remain incomplete.

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

The frozen 0.60.0 committed migration chain contains **20 migrations**:

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

Shared release tooling fingerprints **81 critical domain constraints** through `scripts/release_contract.py`.

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

- exact accepted executable head: `c8db446d367284465853850136c31274c8e39370` — **46/46 SUCCESS**;
- tree-equivalent main merge: `e5efe074abb4a277c032b017ae5fb02c5d0d5039` — **35/35 SUCCESS**;
- truth-only main head: `00fdb8d1b583cf418e1c39709fb79ca248e462e4` — **4/4 SUCCESS**;
- frozen external-production manifest: `release/current-rc.json` now points to Resort OS 0.60.0.

Production governance remains fail-closed:

- GitHub `main` branch protection / required-check enforcement is **NOT VERIFIED**;
- Google Drive launch-control permissions are **NOT VERIFIED** and prior audit found public writer exposure;
- external Beget/staging/rollback/device/provider/monitoring/backup/DNS evidence is incomplete;
- explicit final owner cutover approval has not been given.

Therefore the refrozen RC does **not** authorize DNS switch or external production declaration.

## Deployment state

### GO — repository release engineering

Resort OS 0.60.0 is merged, regression-green and deliberately frozen as the internal external-production candidate.

### STOP — external production cutover

External production remains **NOT VERIFIED / CUTOVER STOP** until the launch evidence gate is closed, including:

1. GitHub branch protection / required checks on `main`;
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
12. explicit owner cutover approval.

## Launch rule

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` and `scripts/verify_launch_acceptance.py`.
Canonical frozen external-production manifest: `release/current-rc.json`.

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until every required external/governance evidence gate is VERIFIED.

## Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not reactivate NFC or automatic commercial/payment authority as a side effect of deployment work.
