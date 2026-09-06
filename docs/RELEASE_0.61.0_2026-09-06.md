# THREE CROWNS RESORT OS — RELEASE 0.61.0

Date: 2026-09-06
Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

## Release identity

Repository: `stvelikiy-star/resort-os`
Accepted source PR: `#116` — `audit/full-project-fixes-20260905 -> main`
Accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`
Production source branch: `main`

The accepted PR head completed **59/59 pull-request workflow runs successfully with zero failures**. A direct compare from accepted head to observed main merge returns **0 changed files**.

The main merge triggered 40 push workflows. **38 product/security/migration/staging workflows succeeded**. `Release RC Truth CI` and `Launch Acceptance CI` failed closed by design because the previous manifest still described 0.60.0. This 0.61.0 release-hygiene refreeze updates release truth; it does not weaken those gates.

## Database release contract

Resort OS 0.61.0 freezes:

- **22 committed Prisma migrations**;
- **87 critical domain constraints** from `scripts/release_contract.py`;
- canonical seed **84 rooms / 12 room categories / 48 rate rows**.

Migration ledger:

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

Production/staging migration mechanism remains `npx prisma migrate deploy` only.

## Audit corrections accepted in 0.61.0

- rooms 501/502 canonical intake is corrected to owner-approved two-person basement inventory above the laundry;
- owner-correction regression guards prevent seed/import truth from drifting back to the superseded mansard/single mapping;
- payment idempotency includes normalized actual `paid_at`;
- OWNER/MANAGER vs RECEPTION finance/folio actions are aligned between Core and UI;
- `APP_ENV=production|prod` without `DATABASE_URL` fails closed;
- missed 3-day housekeeping services use the latest-due catch-up policy instead of creating a burst of historical OPEN tasks;
- canonical release workflows are required to cover `main`;
- active Dining table uniqueness and Dining production snapshot integrity are part of the committed release contract.

## Product boundary

Canonical architecture:

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

The release contains repository/CI-gated contracts for Public Site RU/KG/EN, Core booking availability/pricing, ReservationRequest boundary, PMS chessboard/reception, Stay/RoomAssignment, Guest OS/CRM, MAID/TECHNICIAN/DINING staff flows, Kitchen/Dining, Group Booking, Guest Folio/Finance, CMS/Media, Service Point QR, messaging inbox, AI/n8n boundaries, backup/restore tooling and owner analytics.

`ReservationRequest != Reservation` and operational/service charges are not proof of actual Payment.

NFC acquiring remains outside active V1. Real bank acquiring, real TTLock actuation and real messaging-provider delivery are not considered live without real provider/hardware E2E evidence.

## Production GO / STOP

Repository release engineering: **GO** after this refreeze PR is green and merged.

External production cutover: **STOP** until all required evidence is VERIFIED, including:

1. GitHub `main` branch protection / required checks (#91);
2. Google Drive launch-control permission remediation (#100);
3. actual Beget host/account preflight;
4. verified rollback package for current live `3korony.com`;
5. isolated external HTTPS/WSS staging;
6. real 84-room staging reconciliation;
7. external public-truth probe;
8. real-device acceptance;
9. provider E2E for every launch-enabled provider;
10. monitoring/alerting evidence;
11. fresh pre-cutover DB backup plus off-site copy;
12. exact DNS rollback capture;
13. explicit owner cutover approval.

This release record is repository evidence only. It does **not** claim `PRODUCTION READY`, `LIVE` or `VERIFIED IN PRODUCTION`.
