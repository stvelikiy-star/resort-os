# RESORT OS — CURRENT STATE

Version: 6.1  
Date: 2026-09-07  
Status: RESORT OS 0.62.1 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted source PR: `#125` — `audit/internal-hardening-20260907 -> main`.  
Accepted executable head: `b3bb0c1be4c522d765509796ddd1d32e8606dc89`.  
Observed tree-equivalent main merge: `7f689458b2cf507d76a8c54fbe164e9492f79aca`.  
Production source branch: `main`.

Evidence:
- PR #125 accepted head: **28/28 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent;
- observed merge: **23/23 eligible product/security/migration/staging workflows SUCCESS**;
- one additional `Release RC Truth CI` push run failed closed exactly because the prior 0.62.0 manifest detected executable drift; 0.62.1 is the controlled refreeze.

Machine authority: `release/current-rc.json`.

## Hardening accepted in 0.62.1

- historical `/admin/demo` is fail-closed with 404 instead of bypassing the authenticated AdminShell;
- Kitchen draft bootstrap is OWNER/MANAGER-only outside production;
- Kitchen draft bootstrap is 404 in production even for OWNER/MANAGER;
- DINING_STAFF bootstrap denial is covered by negative E2E;
- management CI rejects any `apps/web/**` change during this frozen-site phase;
- strict internal hardening assertions cover release truth, auth/RBAC markers, production-env safety, 84-room intake, 12-category normalization, 48 rate rows, Kitchen boundaries and external acceptance fail-closed behavior.

## Architecture authority

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`. OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee reservations, invent payment policy, check in/out, refund, bypass Core pricing/availability or write generic business truth directly to PostgreSQL.

Real bank/TTLock remains provider-gated. NFC acquiring/wallet remains outside active V1.

## Database/property release contract

Release 0.62.1 retains **22 committed migrations / 87 critical domain constraints**.  
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

Production/staging schema changes use `npx prisma migrate deploy`; never replace the committed ledger with `prisma db push`.

## Repository-verified management contour

Verified contours include Dashboard, PMS/supershakhmatka, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Guest OS, Dining/Kitchen, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports/Analytics, Operations, Staff/RBAC, Inbox, automation contracts, backup/restore and release/staging/package gates.

The public website is frozen by owner instruction and was not changed by PR #125.

## Owner-approved priority change

GitHub branch protection and Google Drive public-writer remediation remain recommended security improvements, but **are not blockers for the current internal-release phase** by explicit owner decision. They can be handled later.

Beget/VPS deployment is intentionally postponed to the **final external phase**. Until that phase is executed, external staging, live rollback, devices, providers, monitoring, real backups and DNS cutover remain unverified.

Production cutover therefore remains **EXTERNAL PRODUCTION CUTOVER STOP** for the simple reason that the external phase has not been executed yet, not because GitHub protection or Drive permissions block internal work.

Canonical launch procedure: `knowledge/09_LAUNCH_ACCEPTANCE.md`.  
Canonical deployment procedure: `docs/DEPLOYMENT_RUNBOOK.md`.  
Canonical release manifest: `release/current-rc.json`.
