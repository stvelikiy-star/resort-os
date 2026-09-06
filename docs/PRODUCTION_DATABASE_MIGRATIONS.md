# Three Crowns — production database migration gate

Date: 2026-09-06
Release: `0.61.0`
Status: **COMMITTED / CLEAN-DEPLOY VERIFIED IN REPOSITORY CI / BACKUP-RESTORE VERIFIED IN CI / EXTERNAL PRODUCTION NOT EXECUTED**

This document defines the database migration boundary for Three Crowns Resort OS. It does not prove that migrations were run against a real production database.

## Canonical migration ledger

Production/staging schema changes are represented only by committed Prisma migrations.

Exact frozen Resort OS 0.61.0 ledger — **22 migrations**:

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

The exact ledger is maintained in `scripts/release_contract.py` and verified fail-closed by CI.

## Shared release constraint contract

The 0.61.0 release fingerprints **87 critical domain constraints** through `CRITICAL_CONSTRAINTS` in `scripts/release_contract.py`.

The fingerprint covers Hotel / Payment / Guest / Operations / Service Point / Kitchen / Dining / Group Booking / Folio / CMS Media boundaries, including:

- valid rate/request/reservation/inventory dates;
- positive/nonnegative financial bounds;
- active room overlap protection;
- Guest Services context/time guards;
- Owner analytics/Growth guards;
- Service Point QR/context and paid-access guards;
- Kitchen order/menu totals and availability guards;
- Dining publication/reservation/floor/session/table-state guards;
- active table uniqueness and Dining production snapshot meal/count/fingerprint/reason integrity;
- Guest Offer target/window/event guards;
- Group Booking invariants;
- Guest Folio receivable/payment separation;
- CMS Media asset/publication/slot invariants.

Foreign keys, uniqueness and migration-specific trigger invariants are additionally checked by migration/domain tests.

## Canonical property baseline

Repository acceptance uses the canonical property dataset:

- 84 physical rooms;
- 12 room categories;
- 48 rate rows.

Rooms 501/502 are owner-approved two-person basement inventory above the laundry. The superseded mansard/single mapping must not be reintroduced through seed/import/reconciliation.

Physical room intake is closed. Real target reconciliation remains an external deployment evidence step.

## Rules

1. `prisma db push` is allowed only for disposable development/test databases.
2. Production/staging uses `npx prisma migrate deploy`.
3. Never use `migrate resolve` to hide schema drift.
4. Never run destructive reset commands against production.
5. Custom PostgreSQL constraints must remain in committed migration history.
6. Any forward migration must update `scripts/release_contract.py` and release/backup verification in the same change.
7. Backup -> isolated restore verification is required before cutover.
8. Production requires a fresh real backup even though repository backup/restore is CI-verified.

## Repository evidence for 0.61.0

Accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`.
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.

Repository CI verifies the current 22-migration / 87-constraint contract, including:

- Prisma schema validation;
- clean PostgreSQL migration deploy from empty DB;
- exact migration ledger;
- canonical 84-room / 12-category / 48-rate integrity;
- Kitchen/Dining table, status, price, publication, reservation, session and idempotency invariants;
- Dining production snapshot integrity;
- Guest OS, Guest Offers, Guest Service settings and Housekeeping charge constraints;
- Service Point QR / paid-access boundaries;
- Group Booking and Guest Folio constraints;
- CMS Media asset/slot constraints;
- Resort Core/PMS/business invariant regressions;
- backup creation and isolated restore tooling;
- production-like staging migration/application startup contracts.

Repository CI is not proof that the real target DB has been migrated.

## Fresh staging / production database

Use the exact accepted release SHA from `release/current-rc.json` and run:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
```

Then run production preflight with real target environment/database evidence:

```bash
python scripts/production_preflight.py
```

Do not disable migration-history verification merely to make preflight pass.

## Existing database created outside migrations

If an existing external DB was historically created with `db push` or manual SQL:

1. take and verify a backup;
2. compare the real schema against the exact committed migration-defined schema;
3. fix drift explicitly;
4. only if baseline equivalence is actually proven, use `migrate resolve` for bookkeeping where appropriate;
5. run `npx prisma migrate status`;
6. run production preflight;
7. preserve evidence of comparison/migration result.

`migrate resolve` never repairs schema.

## Backup / restore gate

Create backup:

```bash
BACKUP_DIR=/secure/path python scripts/database_backup.py
```

Restore into an isolated verification database:

```bash
BACKUP_FILE=/secure/path/three-crowns-....dump \
BACKUP_MANIFEST=/secure/path/three-crowns-....manifest.json \
RESTORE_DATABASE_URL=postgresql://.../resort_os_restore \
python scripts/database_restore_verify.py
```

Repository CI proves the mechanism against the release contract. Production still needs a new backup from the actual target DB with checksum/timestamp/off-site copy/restore ownership evidence.

## Production boundary

Current state is **migration-engineering ready, external production evidence incomplete**.

Do not claim production migration success until the actual target DB has:

- fresh backup evidence;
- exact accepted release SHA/image set;
- `migrate deploy` result;
- exact **22-migration** ledger;
- exact **87-constraint** shared release fingerprint plus migration-specific invariants;
- readiness/smoke result;
- tested rollback/restore path;
- verified off-site backup copy.

See `knowledge/09_LAUNCH_ACCEPTANCE.md` for the full gate. **EXTERNAL PRODUCTION CUTOVER STOP** remains in force until all required external evidence is VERIFIED.
