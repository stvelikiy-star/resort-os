# RESORT OS — CURRENT STATE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted test/safety source PR: `#135` — `test/load-stress-harness-20260907 -> main`.  
Accepted executable/release-boundary head: `d851c5c64a103ab263b977b3b07c970f29676783`.  
Observed tree-equivalent main merge: `b477e76a32b7fc0fdf8a349cda400c7fa12bc297`.  
Production source branch: `main`.

Evidence:
- PR #135 exact tested head: **22/22 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent; GitHub compare reports zero changed files;
- observed main merge: **20/20 applicable non-truth workflows SUCCESS**;
- one additional `Release RC Truth CI` push run failed closed because the previous 0.62.2 manifest correctly detected the new load-test safety boundary; this same-version refreeze is the controlled correction.

Machine authority: `release/current-rc.json`.

## Hardening accepted in the final 0.62.2 boundary

- all prior 0.62.2 mutation, route-uniqueness, migration and localhost-only CI hardening remains in force;
- the new k6 read-pressure harness is explicitly limited to `ci|test|staging`;
- `3korony.com` and `www.3korony.com` are explicitly blocked as load-test targets;
- the harness uses only readiness, booking availability and optional authenticated PMS-grid reads; it does not mutate reservations, payments, stays or provider state;
- real capacity is **not** claimed until this harness is executed against isolated external Beget/VPS staging with CPU/RAM/PostgreSQL/Caddy observations;
- active FastAPI runtime version remains `0.62.2`.

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

Verified contours include Dashboard, PMS/supershakhmatka, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Guest OS, Dining/Kitchen, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports/Analytics, Operations, Staff/RBAC, Inbox, automation contracts, backup/restore, release/staging/package gates and the guarded load-test contract.

The public website is frozen by owner instruction. PR #135 accepts **zero `apps/web/**` changes**; Public Web is only built as compatibility evidence.

## Current external boundary

GitHub `main` branch protection and Google Drive public-writer remediation remain unresolved launch-security items. Beget/VPS external runtime access, legacy rollback, HTTPS/WSS staging, real devices/providers, monitoring, actual load execution, fresh backup/restore/off-site evidence and DNS rollback are not claimed by repository CI.

External production remains **EXTERNAL PRODUCTION CUTOVER STOP** until those items and explicit owner GO are complete.
