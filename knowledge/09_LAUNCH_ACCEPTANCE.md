# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Date: 2026-09-01
Status: INTERNAL RELEASE CANDIDATE / EXTERNAL CUTOVER STOP
Canonical: YES

This document separates repository/CI evidence from external production evidence. It must not be used to imply that the system is live.

## 1. Current repository boundary

Integration branch: `integration/site-pms-cms-20260827`.

Current integration head: `42798b3fd360b5f5a6a4eb2124b1231702c99eea`.
Latest tested exact PR head: `da3cc80f3c13973f799c01ddd8ad64ed79c17f6f`.

The merge commit has **0 changed files** versus the tested PR head. That exact PR head completed **20/20 triggered workflow contours successfully**, including Resort Core, Full Staging, Production Package, Public Browser, Public Truth, dependency security, realtime, operations, backup/restore and the Site Content Runtime regression.

Earlier closed product gates retain their own exact-head evidence. A merge commit containing the same reviewed tree is not a substitute for independent external acceptance.

## 2. Canonical database release contract

Exact committed migration ledger:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`

Production migration mechanism: `npx prisma migrate deploy`.

Critical PostgreSQL constraint fingerprint is maintained in `scripts/release_contract.py` and currently contains 27 constraints.

## 3. What is repository/CI verified

The repository contains and CI exercises:

- public site truth and RU/KG/EN browser acceptance;
- CMS -> Core -> public runtime with locale-safe fallback/ownership;
- ReservationRequest/Core boundary;
- compact owner PMS grid and full PMS mutation lifecycle;
- Reception/Admin RBAC;
- canonical Stay and RoomAssignment lifecycle;
- Room QR / PIN / GuestSession access;
- Guest OS requests and Staff role routing;
- Guest CRM factual Stay/relocation/history/preferences;
- Guest Services Center;
- Finance & operational control;
- Owner Intelligence / Control / Growth / Dashboard analytics;
- unified inbox, AI draft authority boundary and n8n contracts;
- anonymous Service Point QR operations;
- migration baseline and backup -> clean restore;
- dependency/security inspections;
- single-server production package and CI-local Full Staging;
- NFC deferred scope: NFC payment routes remain outside active V1 composition.

Physical room import gate #38 is **CLOSED / COMPLETED** for the canonical 84-room / 12-category register and safe importer contract. This is not external staging reconciliation evidence.

CI verification is not external production evidence.

## 4. External hard blockers

Production cutover remains STOP until all required items below have real evidence:

- room reconciliation on the actual external staging database against the closed #38 canonical register: importer dry-run -> diff review -> safe apply/result evidence;
- non-destructive preflight on the actual Beget host/account/network;
- verified rollback backup of the currently live `3korony.com` target, including DNS/config/data/media where applicable;
- isolated external HTTPS/WSS staging on the real network;
- external public-truth probe against that staging deployment;
- real-device acceptance on iPhone, Android, desktop and Telegram/staff surfaces;
- real provider E2E for every messaging provider that will be enabled at launch;
- monitoring/alerting evidence on real infrastructure;
- fresh pre-cutover backup evidence;
- exact DNS rollback capture;
- explicit final owner approval for the production/DNS switch.

Do **not** reopen room-data collection as a launch requirement. The remaining room gate is real-target reconciliation only.

## 5. Fail-closed launch evidence

Template: `release/launch-evidence.example.json`.

Verifier: `scripts/verify_launch_acceptance.py`.

Repository check:

```bash
python scripts/verify_launch_acceptance.py --mode repository
```

Cutover check after real evidence has been collected into a separate non-secret manifest:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha <exact-accepted-release-sha>
```

Required external room evidence key is `room_reconciliation`. Historical `owner_room_register` is obsolete and rejected by the verifier because #38 is already closed.

The verifier validates supplied evidence metadata and fails closed on missing gates. It does not manufacture, infer or independently observe external evidence.

Do not commit credentials, provider tokens, database passwords or other production secrets into the evidence manifest.

## 6. Production authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot guarantee a Reservation, confirm payment, invent a fixed prepayment percentage or bypass Core availability/pricing.

NFC acquiring/wallet remains deferred and must not be activated as a side effect of launch acceptance.

## 7. Cutover sequence

After all external blockers are VERIFIED:

1. freeze exact accepted release SHA/image set;
2. take fresh pre-cutover backup;
3. confirm legacy rollback package and DNS rollback target;
4. rerun host/preflight and production preflight;
5. confirm external staging, room reconciliation and device/provider evidence;
6. obtain explicit owner cutover approval;
7. deploy exact accepted release;
8. run readiness/smoke before public switch;
9. switch routing/DNS in the approved window;
10. run public truth, booking, PMS, Guest OS, Staff and WSS smoke checks;
11. monitor errors, database and containers;
12. roll back immediately if acceptance criteria fail.

Until step 6 is complete, status remains `PRODUCTION CUTOVER STOP`.
