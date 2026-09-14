# RESORT OS — CURRENT STATE

Version: 6.5  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST VERIFIED / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != FULL TEST VERIFIED != EXTERNAL PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted source PR: `#164` — `fix/public-request-sent-copy-20260914 -> main`.  
Accepted executable/release-boundary head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

Evidence:
- PR #164 exact tested head: **26/26 pull-request workflows SUCCESS, 0 failures**;
- the merge is intentionally not tree-equivalent because PR #163 landed while PR #164 was open;
- the only accepted tested-head -> merge drift is the exact PR #163 operational set: `.github/workflows/main-pr-merge-guard-ci.yml`, `scripts/main_pr_merge_guard.py`, `scripts/release_rc_truth_guard.py`;
- first PR #164 main push: **25/26 workflows SUCCESS**; the only failure was `Release RC Truth CI`, correctly failing closed on the previous frozen boundary;
- this same-version refreeze records the new product truth without weakening the guard.

Machine authority: `release/current-rc.json`.  
Strict guard: `scripts/release_rc_truth_guard.py`.

## Final accepted product contour

Architecture authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

The accepted contour includes:
- Public site with the exact server-confirmed Russian booking-request success message: `Заявка отправлена. Номер заявки <id>. Менеджер свяжется с вами для согласования условий и предоплаты.`; the request still explicitly remains not yet a confirmed reservation;
- Admin/PMS with Dashboard, chessboard, Rates/Seasons, Group Booking, CRM/Requests, Reception, Guest Services/history, Offers, Finance, Reports/Analytics, Operations, Staff/RBAC and Inbox;
- **Marketing remains part of final Admin/Core**, including consent/attribution and automation contours;
- Agent CRM: cards, booking linkage, period reports, booked value, received payments, room nights, contact history and next-contact tracking;
- dated `MAINTENANCE` and `MANUAL` room holds for owner/staff/guest/service/other use;
- safe booking move/reschedule: drag/drop -> Resort Core preview -> explicit `Подтвердить и сохранить график` -> commit;
- extra-bed Core rule: forbidden for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD`; allowed elsewhere with server recalculation;
- returning guest accommodation discount: automatic **10%** after a prior `CHECKED_OUT` stay; alternative manager discount remains explicit and auditable;
- Guest OS, Staff/housekeeping/maintenance/voice, Kitchen/Dining, Service Point QR, realtime/WebSocket, backup/restore and release gates.

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment, guarantee reservations, invent pricing/payment policy, check in/out, refund or bypass Core availability/pricing.

Real bank/MKassa/TTHotel/TTLock remains provider-gated. NFC acquiring/wallet remains outside active V1.

## Database/property release contract

Release `0.62.2` remains **24 committed migrations / 93 critical domain constraints**.  
Canonical property baseline remains **84 rooms / 12 room categories / 48 rate rows**.  
Migration authority: `docs/PRODUCTION_DATABASE_MIGRATIONS.md`.

Canonical migration ledger, in exact deployment order:
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
23. `z99_marketing_consent_attribution_20260912`
24. `zz100_owner_ops_corrections_20260914`

External staging/production schema changes use only `npx prisma migrate deploy`; `prisma db push` is not release evidence.

## Railway Full Test evidence

Railway project `Three Crowns Full Test` has API, Web, Admin, Staff and PostgreSQL in successful runtime state. The application deployment used the accepted owner-operations merge boundary; subsequent repository-only monitoring/release changes do not change that runtime.

Verified Full Test evidence includes:
- all **24** migrations applied and readiness HTTP 200;
- canonical 84 rooms / 12 categories / 48 rates;
- external HTTPS checks and WSS-path checks from GitHub runners;
- scheduled external smoke every 6 hours;
- daily Chromium acceptance for Public/Admin/Staff without credentials or business writes;
- explicit `ON_FAILURE` self-healing policy for API/Web/Admin/Staff;
- read-only k6 baseline 10 -> 25 -> 50 VU: **32,229 HTTP requests, 0% HTTP failures, overall p95 38.49 ms, availability p95 42.25 ms**;
- observed load peaks: API CPU about 49.9%, PostgreSQL CPU about 25.6%, with recovery after the test;
- repository PostgreSQL backup -> clean restore CI green.

This proves the integrated Full Test contour. It does **not** authorize real hotel production cutover.

## Repository safety

GitHub repository rulesets are currently absent, so true branch protection is not yet proven. Until administrative protection is enabled, `main` has a fail-closed CI merge guard requiring canonical PR merge commits. This is a safety signal, not a substitute for GitHub branch protection.

## Current external boundary

Still not production-verified/closed:
- actual GitHub `main` branch protection/required checks at the platform administration layer;
- public Google Drive writer-grant remediation because precise permission records are not exposed by the current connector;
- authorized real Beget/VPS/production execution path and target reconciliation;
- executable legacy-live rollback package and restore rehearsal on the actual target;
- final production HTTPS/WSS and real-device acceptance on hotel domains;
- real launch-enabled MKassa/TTHotel/TTLock provider/hardware E2E;
- fresh actual-target backup -> isolated clean restore -> verified off-site copy;
- immutable production SHA/image/runtime linkage;
- production DNS rollback evidence;
- explicit owner GO for production/DNS/provider activation.

Full Test load testing, external monitoring and self-healing evidence are now verified and are no longer open Full Test blockers.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
