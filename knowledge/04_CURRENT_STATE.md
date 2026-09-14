# RESORT OS — CURRENT STATE

Version: 6.4  
Date: 2026-09-14  
Status: RESORT OS 0.62.2 INTERNAL RC REFROZEN / FULL TEST DEPLOYED / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != FULL TEST VERIFIED != EXTERNAL PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted source PR: `#157` — `feat/owner-ops-corrections-20260914 -> main`.  
Accepted executable/release-boundary head: `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`.  
Observed tree-equivalent main merge: `b13bacad3f2e923f51354b1839371d07179b2e8c`.  
Production source branch: `main`.

Evidence:
- PR #157 exact tested head: **52/52 pull-request workflows SUCCESS, 0 failures**;
- accepted head and observed merge use the same Git tree `f8991f2f65d837dd16745b43582b5c97292548b6`;
- first merge push: **37/39 workflows SUCCESS**; the only two failures were `Release RC Truth CI` and `Launch Acceptance CI`, both correctly failing closed because the previous frozen manifest still pointed at the 2026-09-07 release boundary;
- this same-version refreeze updates release truth without weakening the fail-closed controls.

Machine authority: `release/current-rc.json`.  
Strict guard: `scripts/release_rc_truth_guard.py`.

## Final accepted product contour

Architecture authority:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

The accepted contour includes:
- Public site with server-confirmed booking-request success state, current mobile/i18n/media work and marketing consent/privacy surface;
- Admin/PMS with Dashboard, supershakhmatka, Rates/Seasons, Group Booking, CRM/Requests, Reception, Guest Services, Guest history, Offers, Finance, Reports/Analytics, Operations, Staff/RBAC and Inbox;
- **Marketing remains part of the final Admin/Core**, including the marketing consent/attribution and automation contour;
- Agent CRM: cards, booking linkage, period filtering/reporting, booked value, received payments, room nights, contact history and next-contact tracking;
- Reception agent filter and agent context on reservations;
- dated `MAINTENANCE` and `MANUAL` room holds for owner/staff/guest/service/other use;
- safe booking move/reschedule flow: drag/drop -> Resort Core preview -> explicit `Подтвердить и сохранить график` -> commit;
- extra-bed Core rule: forbidden for `DOUBLE_STANDARD_BASEMENT`, `DOUBLE_IMPROVED`, `TWO_ROOM_STANDARD`; allowed for other categories with server recalculation;
- returning guest accommodation discount: automatic **10%** after a prior `CHECKED_OUT` stay; alternative manager discount remains explicit and auditable;
- Guest OS, Staff/housekeeping/maintenance/voice, Kitchen/Dining, Service Point QR, realtime/WebSocket, backup/restore and release gates.

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation/payment authority. AI/n8n cannot confirm payment, guarantee reservations, invent pricing/payment policy, check in/out, refund, bypass Core availability/pricing or write generic business truth directly to PostgreSQL.

Real bank/TTLock remains provider-gated. NFC acquiring/wallet remains outside active V1.

## Database/property release contract

Release 0.62.2 now has **24 committed migrations / 93 critical domain constraints**.  
Canonical property baseline remains **84 rooms / 12 room categories / 48 rate rows**.

Canonical 24-migration ledger:
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

The `zz100` prefix is intentional so Prisma lexical ordering applies it after the `z99` Marketing migration. External staging/production schema changes use only `npx prisma migrate deploy`; `prisma db push` is not release evidence.

## Railway Full Test evidence

Project `Three Crowns Full Test` has API, Web, Admin and Staff deployed from main merge SHA `b13bacad3f2e923f51354b1839371d07179b2e8c`; all four latest deployments are `SUCCESS`.

API startup evidence on 2026-09-14:
- found 24 migrations;
- successfully applied `z99_marketing_consent_attribution_20260912`;
- successfully applied `zz100_owner_ops_corrections_20260914`;
- seed verified 84 rooms / 12 room types / 48 rate rows;
- existing Full Test reservation/stay data was preserved rather than reset;
- `/health/ready` returned HTTP 200.

This proves the integrated Full Test contour. It does **not** authorize real hotel production cutover.

## Current external boundary

Still not production-verified/closed:
- GitHub `main` branch protection and required checks;
- removal/downgrade of public Google Drive writer grants;
- authorized real Beget/VPS/production execution path and target reconciliation;
- executable legacy rollback package and restore rehearsal;
- external production HTTPS/WSS and real-device acceptance;
- launch-enabled real bank/MKassa/TTLock E2E where applicable;
- actual load/stress execution with CPU/RAM/PostgreSQL/network observations;
- production monitoring, alerts and restart/self-healing evidence;
- fresh actual-target backup -> clean restore -> off-site copy evidence;
- immutable release/image/runtime linkage and DNS rollback;
- explicit owner GO for production/DNS/provider activation.

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force.
