# RESORT OS — CURRENT STATE

Version: 6.2  
Date: 2026-09-07  
Status: RESORT OS 0.62.2 INTERNAL RC FROZEN / REPOSITORY GREEN / EXTERNAL PRODUCTION CUTOVER STOP  
Canonical: YES

**IMPLEMENTED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Release identity

Repository: `stvelikiy-star/resort-os`.  
Accepted safety source PR: `#132` — `hardening/local-mutating-ci-runner-20260907 -> main`.  
Accepted executable/release-boundary head: `ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd`.  
Observed tree-equivalent main merge: `7cf4b5a3c4164f7224a2fd70807cecf40cfb42bc`.  
Production source branch: `main`.

Evidence:
- PR #132 exact tested head: **25/25 workflows SUCCESS, 0 failures**;
- accepted head and observed merge are tree-equivalent; GitHub compare reports zero changed files;
- observed main merge: **23/23 applicable non-truth workflows SUCCESS**;
- one additional `Release RC Truth CI` push run failed closed because the previous 0.62.2 manifest correctly detected safety-boundary drift; this controlled 0.62.2 safety refreeze updates that boundary without changing runtime version.

Machine authority: `release/current-rc.json`.

## Hardening accepted in the final 0.62.2 safety boundary

- Kitchen mutation authority and active-route uniqueness hardening from the original 0.62.2 freeze remain in force;
- synthetic demo/operations mutation utilities fail closed unless an explicit allowed non-production environment is supplied;
- legacy `release_candidate_check.sh` mutating/db-push path is retired;
- migration baseline generation is restricted to explicit `development|test|ci` disposable environments;
- Owner Control V2 mutating E2E requires explicit `ci|test`, localhost-only Resort Core/PostgreSQL and explicit credentials;
- Guest OS Core, Owner Intelligence, Owner Growth and PMS resize mutating E2E workflows run only through the allowlisted localhost-only `scripts/run_local_mutating_ci.py` guard;
- Management Final Acceptance regression-checks these safety boundaries;
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

Verified contours include Dashboard, PMS/supershakhmatka, Rates/Seasons, Group Booking, CRM, Reception, Guest Services, Guest OS, Dining/Kitchen, Service Settings, Guests/History, Guest Offers, QR, Growth, Finance, Reports/Analytics, Operations, Staff/RBAC, Inbox, automation contracts, backup/restore and release/staging/package gates.

The public website is frozen by owner instruction. PRs #129–#132 and this refreeze accept **zero `apps/web/**` changes**; Public Web is only built as compatibility evidence.

## Current plan boundary

GitHub branch protection and Google Drive public-writer remediation remain advisory/deferred per owner decision and do not block the current internal RC. Beget/VPS is deliberately the final phase.

External production remains **EXTERNAL PRODUCTION CUTOVER STOP**. Real host, rollback, HTTPS/WSS staging, real devices/providers, monitoring, fresh backup/restore/off-site evidence and explicit owner GO are not claimed by repository CI.
