# THREE CROWNS RESORT OS — LAUNCH ACCEPTANCE

Date: 2026-09-02
Status: **INTERNAL RC FROZEN / EXTERNAL CUTOVER STOP**
Canonical: YES

This document separates repository/CI evidence from real external production evidence. Nothing below implies that the new Resort OS is live.

## 1. Current repository boundary

Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `ce2d8ecde43c294162a782f7912425ced5258f99`.
Observed integration merge: `05777f3371bd42b4c4cc9a8d6d68fa9b482b238c`.

The accepted head is the exact PR #102 product hardening head. It completed **17/17 non-RC workflows successfully with zero failures**. Release RC Truth failed before refreeze by design because the previous RC was still frozen.

The observed integration merge has **0 changed files** versus the tested executable head. Therefore the merged executable tree is identical to the tested tree.

Subsequent integration merge `beb5cc59a42256c5cfd50c0c336b4fe611ed1c8c` is documentation-only release hygiene. The RC guard allows only the specifically reviewed `docs/README.md` and `docs/STAGING_RUNBOOK_2026-08-28.md` as additional hygiene paths.

Machine-readable boundary: `release/current-rc.json`.
Guard: `scripts/release_rc_truth_guard.py`.

`main` is not a production source. It must not be used for external deployment or cutover while stale relative to the accepted integration RC.

## 2. Canonical database and room release contract

Exact migration ledger:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`

External staging/production migration mechanism: `npx prisma migrate deploy`.

The shared release contract contains 27 critical hotel/payment constraints. Prisma and `@prisma/client` are pinned exactly to `6.12.0`; deterministic lockfile installs and zero HIGH/CRITICAL database dependency findings are required.

Canonical physical-room authority:

- `data-intake/rooms.csv` — 84 rooms / 12 categories;
- `data-intake/room-register-owner-approval.json` — checksum-bound OWNER_APPROVED evidence.

Room gate #38 is CLOSED. Do not reopen the room questionnaire and do not promote an old Google room/import sheet into a second mutable authority.

Remaining external room evidence is target reconciliation only:

`dry-run -> exact diff review -> safe apply -> zero diff`.

## 3. Repository/CI verified product boundaries

The accepted executable tree includes regression-gated contracts for:

- public site RU/KG/EN truth and browser behavior;
- Transfer before Tours;
- Core availability/pricing;
- `ReservationRequest != Reservation`;
- no fixed 30% system rule;
- no automatic payment/Reservation confirmation;
- PMS grid, realtime and mutation lifecycle;
- Reception/Admin RBAC;
- Stay and RoomAssignment;
- Room QR / PIN / GuestSession;
- Guest CRM/history/preferences/audit;
- Guest Services and Staff operations;
- anonymous Service Point QR;
- Kitchen Admin, factual tables, menu and order lifecycle;
- Kitchen finance isolation;
- Finance/Owner operational controls;
- unified inbox and provider evidence model;
- AI draft authority and n8n/Core boundary;
- backup -> clean restore and production-package contracts;
- exact release-SHA/image linkage tooling;
- external-staging orchestration tooling;
- active-V1 NFC exclusion.

PR #102 additionally locks the customer-facing Core AI facts returned by `/api/v1/automation/read/hotel-facts`:

- check-in `14:00`;
- checkout `12:00`;
- gym absent;
- sports grounds absent;
- sauna winter-only, 5000 KGS/hour, approximately 4–5 people;
- billiards 500 KGS/hour;
- table tennis free for staying guests;
- parking approximately 20–30 cars, free for staying guests;
- laundry and conference halls `UNKNOWN_DO_NOT_PROMOTE`;
- no unverified payment-method/provider enumeration in customer-facing AI context;
- launch payment routes/providers remain `NOT_VERIFIED_FOR_LAUNCH` until real evidence exists.

The n8n Core contract tests these facts through a running FastAPI/Core instance. Repository tests still do not prove real provider delivery.

## 4. Production authority boundary

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot guarantee a Reservation, confirm payment, invent a fixed prepayment percentage/payment route, bypass Core availability/pricing, or write PostgreSQL directly.

Growth outbound authority remains `NONE_AUTOMATIC`.

Kitchen operational totals do not automatically create Hotel Payment and do not change accommodation totals.

NFC acquiring/wallet remains DEFERRED and must not be activated during V1 launch work.

Google Drive/Sheets remain knowledge/control/mirror surfaces, not transaction truth.

## 5. External hard blockers

Production remains **EXTERNAL CUTOVER STOP** until all required real evidence below is current and verified:

1. GitHub branch protection/required-check enforcement for the release branch policy.
2. Google Drive launch-control permissions hardened so public writer access cannot alter CURRENT/control data.
3. Non-destructive preflight on the actual host/account/network.
4. Verified rollback package for the currently live legacy `3korony.com`, including factual webroot/database/media/config/DNS decisions, off-site copy and restore rehearsal.
5. Isolated external HTTPS/WSS staging using the exact accepted release.
6. Exact eight-migration deployment ledger on the external staging database.
7. Real staging room reconciliation against the canonical 84-room register to zero diff.
8. External rendered public-truth probe.
9. Real-device acceptance on iPhone Safari, Android Chrome and desktop, plus required Telegram/Staff/Kitchen surfaces.
10. Real E2E for every messaging/payment provider that will actually be enabled at launch. Disabled providers are not launch blockers.
11. Real monitoring/alert delivery evidence.
12. Backup-age/off-site/restore evidence.
13. Fresh pre-cutover backup.
14. Exact DNS rollback capture.
15. Explicit OWNER GO for the production/DNS switch.

CI, Vercel previews, Google Drive documents and templates do not satisfy these external evidence gates.

## 6. Fail-closed repository checks

Canonical repository checks include:

```bash
python scripts/release_rc_truth_guard.py
python scripts/verify_launch_acceptance.py --mode repository
python scripts/beget_deployment_guard.py
```

The release truth guard verifies:

- exact accepted executable SHA;
- exact observed tree-equivalent merge SHA;
- all-success accepted-head workflow count;
- no unexpected product drift after accepted head;
- current canonical docs contain the frozen boundary;
- `main` remains forbidden as production source;
- external evidence flags remain false before real evidence exists.

## 7. External operator sequence when authorized infrastructure access exists

The following is the mandatory order. It is recorded now so the implementation is ready, but it is **not executed while Beget is intentionally out of scope**.

### Phase 0 — exact source boundary

Work only from the accepted integration RC/successor after Release RC Truth is GREEN. Never deploy stale `main`.

### Phase 1 — non-destructive infrastructure preflight

Run the committed host/environment/network preflight against staging-only configuration. Any FAIL blocks deployment.

### Phase 2 — legacy rollback capture and restore proof

Capture the actual current live target using factual database/uploads/config/DNS branches. Store non-secret evidence plus an off-site copy. Rehearse restore and require the committed rollback gate to return GREEN before risking the current live target.

### Phase 3 — isolated external staging

- deploy the exact accepted release SHA;
- use staging-only hostnames/storage/database/secrets;
- run `npx prisma migrate deploy` for the exact eight migrations;
- reconcile canonical 84-room register against the staging target;
- verify deployed image revision labels match the expected SHA;
- do not route production traffic.

### Phase 4 — atomic external acceptance

Use `scripts/external_staging_acceptance.py` against staging-only HTTPS/WSS origins with synthetic-write acknowledgement. Retain the checksum-bound evidence directory. Required result: `RESULT: EXTERNAL STAGING ACCEPTANCE GREEN`.

### Phase 5 — human/external acceptance

After automated external acceptance is GREEN, record:

- iPhone/Android/desktop checks;
- Telegram/Staff/Kitchen checks where enabled/required;
- launch-enabled provider E2E;
- actual monitoring/alert delivery;
- required backup/restore evidence.

### Phase 6 — final cutover verifier

Only after all required external gates plus OWNER GO are real and current, build the non-secret launch evidence manifest and run the cutover verifier against the exact accepted release SHA. DNS/public routing changes remain forbidden before this point.

## 8. Cutover sequence after all gates are green

1. Freeze exact accepted release SHA/images.
2. Take a fresh pre-cutover backup.
3. Confirm legacy rollback package and DNS rollback values.
4. Rerun host/production preflight.
5. Reconfirm staging, room reconciliation and real-device/provider evidence.
6. Obtain explicit OWNER GO.
7. Deploy the exact accepted release.
8. Run readiness/smoke before public routing change.
9. Switch routing/DNS in the approved window.
10. Smoke public truth, booking, PMS, Guest OS, Staff, Kitchen and WSS.
11. Monitor application/database/infrastructure errors.
12. Roll back immediately if acceptance criteria fail.

Until OWNER GO and all preceding evidence exist, status remains **PRODUCTION CUTOVER STOP**.

## 9. Current documentation authority

`docs/README.md` is the current documentation-authority index.

`docs/STAGING_RUNBOOK_2026-08-28.md` is explicitly historical/local staging reference only. Dated handoff/RC/source-reconciliation docs, old ZIP/HTML snapshots and stale Vercel previews cannot override `release/current-rc.json`, Current State or this Launch Acceptance document.

## 10. Current external truth

The new Resort OS is **NOT LIVE** based on repository evidence alone. The current public `3korony.com` must continue to be treated as the legacy site until external cutover evidence proves otherwise.
