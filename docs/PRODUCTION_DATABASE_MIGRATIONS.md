# Three Crowns — production database migration gate

Date: 2026-09-05
Release: `0.60.0`
Status: **COMMITTED / CLEAN-DEPLOY VERIFIED / BACKUP-RESTORE VERIFIED IN CI / EXTERNAL PRODUCTION NOT EXECUTED**

This document defines the database migration boundary for Three Crowns Resort OS. It does not prove that migrations were run against a real production database.

## Canonical migration ledger

Production/staging schema changes are represented only by committed Prisma migrations.

Exact frozen Resort OS 0.60.0 ledger — **20 migrations**:

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

The exact ledger is maintained in `scripts/release_contract.py` and verified fail-closed by CI.

## Rules

1. `prisma db push` is allowed only for disposable development/test databases.
2. Production/staging uses `npx prisma migrate deploy`.
3. Never use `migrate resolve` to hide schema drift.
4. Never run destructive reset commands against production.
5. Custom PostgreSQL constraints must remain in committed migration history.
6. Any new forward migration must update the shared release contract and all release/backup verification in the same change.
7. Backup -> isolated restore verification is required before cutover.
8. Production requires a fresh real backup even though repository backup/restore is CI-verified.

## Current verified repository state

CI verifies:

- Prisma schema validation;
- clean PostgreSQL migration deploy from empty database;
- exact **20-migration** ledger;
- **81 critical domain constraints** from the shared release contract in `scripts/release_contract.py`;
- Kitchen/Dining table, status, price, publication, reservation, session and idempotency constraints;
- Guest OS, Guest Offers, Guest Service settings and Housekeeping charge constraints;
- Service Point QR / paid-access boundaries;
- Group Booking and Guest Folio constraints;
- CMS Media asset/slot constraints;
- 84-room / 12-room-category canonical property integrity;
- 48 accepted rate rows in the production-like property seed;
- Resort Core/PMS/business invariant regressions;
- backup creation and clean restore with the current migration/constraint fingerprint;
- production-like staging migration/application startup path.

The canonical room register is 84 rooms / 12 mapped categories. Real target reconciliation remains an external deployment evidence step.

## Critical database boundary

The canonical domain constraint fingerprint is defined by `CRITICAL_CONSTRAINTS` in `scripts/release_contract.py` and currently contains **81 constraints**.

The fingerprint covers the current Hotel / Payment / Guest / Operations / Service Point / Kitchen / Dining / Group Booking / Folio / CMS Media release boundary, including:

- valid rate/request/reservation/inventory dates;
- nonnegative/positive financial bounds;
- active room overlap protection;
- Guest Services context/time guards;
- Owner analytics/Growth guards;
- Service Point QR/context guards;
- Kitchen order/item/menu constraints;
- Dining publication, reservation, floor/session/table-state guards;
- Guest Offer action/target/window/event guards;
- Group Booking invariants;
- Guest Folio receivable/payment separation;
- CMS Media identity/publication/slot invariants.

Foreign keys, uniqueness and migration-specific triggers are additionally checked by migration/domain tests.

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

## Existing database previously created outside migrations

If an existing external database was historically created with `db push` or manual SQL:

1. take and verify a backup;
2. compare real schema against the exact committed migration-defined schema;
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

Repository CI proves this mechanism against the current release contract. Production still needs a new backup from the actual target database with checksum/timestamp/restore ownership evidence.

## Production boundary

Current state is **migration-engineering ready, external production evidence incomplete**.

Do not claim production migration success until the actual target database has:

- fresh backup evidence;
- exact accepted release SHA/image set;
- `migrate deploy` result;
- exact **20-migration ledger**;
- the **81-constraint** shared release fingerprint plus migration-specific invariants;
- readiness/smoke result;
- tested rollback/restore path;
- verified off-site backup copy.

See `knowledge/09_LAUNCH_ACCEPTANCE.md` for the full cutover gate. **EXTERNAL PRODUCTION CUTOVER STOP** remains in force until all required external evidence is VERIFIED.
