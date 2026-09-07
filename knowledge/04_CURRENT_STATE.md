# RESORT OS — CURRENT STATE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted source PR: `#127` — `audit/kitchen-route-canonicalization-20260907 -> main`.  
Accepted executable head: `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`.  
Observed tree-equivalent main merge: `731e81c2d2a4ccc91fae319b73f0d4b8eb9979b5`.  
Production source branch: `main`.

Evidence:
- PR #127 accepted head: **41/41 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent;
- observed merge: **32/32 eligible product/security/migration/staging workflows SUCCESS**;
- one additional `Release RC Truth CI` push run failed closed exactly because the previous 0.62.1 manifest detected executable drift; 0.62.2 is the controlled refreeze.

Machine authority: `release/current-rc.json`.

## Hardening accepted in 0.62.2

- Kitchen menu mutations no longer depend on FastAPI router registration order;
- legacy operational `POST /api/v1/kitchen/menu/bootstrap-draft` and `PATCH /api/v1/kitchen/menu/{item_id}` routes are stripped before application composition;
- the canonical menu mutation router remains OWNER/MANAGER-authoritative while DINING_STAFF keeps operational read/order/table access;
- active API route uniqueness is now checked at runtime in the main Release Gate: duplicate HTTP method + `/api/...` path pairs fail the release;
- active FastAPI runtime version is `0.62.2` instead of the stale `0.60.0` identity;
- previous 0.62.1 hardening remains in force: `/admin/demo` fail-closed, production Kitchen bootstrap 404, DINING_STAFF mutation denial, strict auth/RBAC/data/release assertions.

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

Verified contours include Dashboard, PMS/supershakhmatka, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Guest OS, Dining/Kitchen, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports/Analytics, Operations, Staff/RBAC, Inbox, automation contracts, backup/restore and release/staging/package gates.

The public website is frozen by owner instruction. PR #127 changed **zero `apps/web/**` files**; Public Web was only built as compatibility evidence.

## Current plan boundary

GitHub branch protection and Google Drive public-writer remediation are advisory/deferred per owner decision and do not block the current internal RC. Beget/VPS is deliberately the final phase.

External production remains **EXTERNAL PRODUCTION CUTOVER STOP**. Real host, rollback, HTTPS/WSS staging, real devices/providers, monitoring, fresh backup/restore/off-site evidence and explicit owner GO are not claimed by repository CI.
