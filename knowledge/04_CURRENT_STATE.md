# RESORT OS — CURRENT STATE

Version: 6.3  
Date: 2026-09-08  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted security source PR: `#143` — `audit/request-body-limits-v2-20260907 -> main`.  
Accepted executable/release-boundary head: `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`.  
Observed tree-equivalent main merge: `c931b7e12973ecb62b8f9595d60f0d7947e7ad8e`.  
Production source branch: `main`.

Evidence:
- PR #143 exact tested head: **24/24 workflows SUCCESS, 0 failures, 0 cancellations**;
- accepted head and observed merge are tree-equivalent; GitHub compare reports zero changed files;
- observed main merge: **23/23 applicable non-truth workflows SUCCESS**;
- one additional `Release RC Truth CI` push run failed closed because the previous 0.62.2 manifest correctly detected executable/security drift after the older frozen boundary; this same-version refreeze is the controlled correction.

Machine authority: `release/current-rc.json`.

## Hardening accepted in the final 0.62.2 boundary

All prior 0.62.2 domain, mutation, migration, route-uniqueness, localhost-only CI and guarded load-test controls remain in force. The current refreeze additionally accepts the audited security changes from PRs #137-#143:

- production runtime images are exactly pinned to the audited security baseline;
- authenticated browser WebSockets use same-origin host routing rather than broad cross-subdomain cookies;
- PMS/Dining WebSocket handshakes enforce browser Origin policy in production;
- Telegram public webhook request bodies are bounded at the edge;
- generic public/admin/staff/API request bodies are bounded at the edge;
- CMS media upload has a dedicated 8 MB edge boundary aligned with FastAPI validation;
- Caddy/realtime/body-limit regression guards are included in CI;
- the browser topology guard distinguishes dedicated Admin media routing from the generic Admin Next proxy;
- active FastAPI runtime version remains `0.62.2`.

The guarded k6 harness remains restricted to `ci|test|staging`, explicitly blocks `3korony.com` / `www.3korony.com`, and does not mutate reservations, payments, stays or provider state. Real capacity is **not** claimed until isolated external staging is load-tested with resource observations.

## Architecture authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee reservations, invent payment policy, check in/out, refund, bypass Core pricing/availability or write generic business truth directly to PostgreSQL.

Real bank/TTLock remains provider-gated. NFC acquiring/wallet remains outside active V1.

## Database/property release contract

Release 0.62.2 retains **22 committed migrations / 87 critical domain constraints**.  
Canonical property baseline remains **84 rooms / 12 room categories / 48 rate rows**.  
Rooms 501/502 remain owner-approved two-person basement rooms above the laundry.

Canonical 22-migration ledger:
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

External staging/production schema changes use `npx prisma migrate deploy`; never use `prisma db push` as release evidence.

## Repository-verified management contour

Verified repository contours include Dashboard, PMS/supershakhmatka, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Guest OS, Dining/Kitchen, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports/Analytics, Operations, Staff/RBAC, Inbox, automation contracts, backup/restore, release/staging/package gates, guarded load-test contract, production runtime pinning, same-origin browser realtime, WebSocket Origin security and request-body limits.

The public website is frozen by owner instruction. PRs #137-#143 accept **zero `apps/web/**` product-source changes**; Public Web is built only as compatibility evidence.

## Current external boundary

The following are still not production-verified:

- GitHub `main` branch protection / required checks;
- removal or downgrade of public Google Drive writer grants;
- authorized Beget/VPS execution path;
- real legacy-live rollback package and restore rehearsal;
- exact 22 migrations and zero-diff 84-room reconciliation on the target database;
- external HTTPS/WSS staging;
- real iPhone/Android/desktop/Staff/Kitchen device acceptance;
- launch-enabled bank/TTLock provider E2E, if those providers are enabled;
- real load/stress execution with CPU/RAM/PostgreSQL/Caddy observations;
- production monitoring/alerts and restart/self-healing evidence;
- fresh backup -> clean restore -> off-site copy evidence;
- immutable release/image/runtime linkage and DNS rollback.

External production remains **EXTERNAL PRODUCTION CUTOVER STOP** until all required evidence and explicit owner GO are complete.
