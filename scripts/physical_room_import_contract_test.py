#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
ROOMS_CSV = ROOT / "data-intake" / "rooms.csv"
APPROVAL = ROOT / "data-intake" / "room-register-owner-approval.json"
IMPORTER = ROOT / "scripts" / "import_physical_rooms.py"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os").replace("?schema=public", "")
PROPERTY_CODE = "THREE_CROWNS"
TARGET_CODE = "112"


def run_import(*args: str, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(IMPORTER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    combined = proc.stdout + proc.stderr
    print(combined, end="")
    if expect_success and proc.returncode != 0:
        raise AssertionError(f"importer failed rc={proc.returncode}:\n{combined}")
    if not expect_success and proc.returncode == 0:
        raise AssertionError(f"importer unexpectedly succeeded:\n{combined}")
    return proc


def canonical_target() -> dict[str, str]:
    with ROOMS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 84
    row = next(item for item in rows if item["room_code"].strip() == TARGET_CODE)
    return row


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.upper() == "UNKNOWN":
        return None
    return value


async def snapshot_room(code: str) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''
            SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",r."areaLabel",
                   r."operationalState"::text AS operational_state,r.notes,rt.code AS room_type_code,
                   to_char(r."updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') AS version
            FROM rooms r
            JOIN room_types rt ON rt.id=r."roomTypeId"
            JOIN properties p ON p.id=r."propertyId"
            WHERE p.code=$1 AND r.code=$2
            ''',
            PROPERTY_CODE,
            code,
        )
        assert row, f"room {code} missing"
        return dict(row)
    finally:
        await conn.close()


async def database_invariants() -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        prop = await conn.fetchrow("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
        assert prop
        return {
            "room_count": int(await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', prop["id"])),
            "room_type_count": int(await conn.fetchval('SELECT count(*) FROM room_types WHERE "propertyId"=$1', prop["id"])),
            "rate_count": int(
                await conn.fetchval(
                    '''SELECT count(*) FROM rate_periods rp JOIN rate_plans plan ON plan.id=rp."ratePlanId" WHERE plan."propertyId"=$1''',
                    prop["id"],
                )
            ),
            "reservation_count": int(await conn.fetchval('SELECT count(*) FROM reservations WHERE "propertyId"=$1', prop["id"])),
            "payment_count": int(
                await conn.fetchval(
                    '''SELECT count(*) FROM payments pay
                       LEFT JOIN reservations r ON r.id=pay."reservationId"
                       LEFT JOIN reservation_requests rr ON rr.id=pay."requestId"
                       WHERE COALESCE(r."propertyId",rr."propertyId")=$1''',
                    prop["id"],
                )
            ),
            "inventory_count": int(
                await conn.fetchval(
                    '''SELECT count(*) FROM inventory_blocks ib JOIN rooms r ON r.id=ib."roomId" WHERE r."propertyId"=$1''',
                    prop["id"],
                )
            ),
        }
    finally:
        await conn.close()


async def corrupt_target_metadata() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            '''
            UPDATE rooms r
            SET name='STALE CI ROOM',"buildingOrZone"='STALE_CI_ZONE',"floorLabel"='STALE_CI_FLOOR',
                "bedConfiguration"='STALE_CI_BEDS',"areaLabel"='999',"operationalState"='DIRTY',
                notes='STALE CI NOTES',"updatedAt"=now()
            FROM properties p
            WHERE r."propertyId"=p.id AND p.code=$1 AND r.code=$2
            ''',
            PROPERTY_CODE,
            TARGET_CODE,
        )
    finally:
        await conn.close()


async def prove_no_active_lock_bypass() -> None:
    """Create a minimal active reservation and prove --apply refuses before mutation.

    The importer is not allowed to reconcile physical metadata while a GUARANTEED or
    CHECKED_IN reservation exists. We insert a self-contained request/reservation and
    remove it after the negative assertion so the later positive apply can proceed.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    request_id = uuid.uuid4()
    reservation_id = uuid.uuid4()
    try:
        prop = await conn.fetchrow("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
        room_type_id = await conn.fetchval(
            '''SELECT "roomTypeId" FROM rooms WHERE "propertyId"=$1 ORDER BY code LIMIT 1''', prop["id"]
        )
        await conn.execute(
            '''INSERT INTO reservation_requests (
                   id,"propertyId",status,source,"guestName",phone,"checkIn","checkOut",adults,children,
                   "desiredRoomTypeId","createdAt","updatedAt"
               ) VALUES ($1,$2,'CONVERTED','CI_PHYSICAL_IMPORT','Import Guard Guest','+996555000001',
                         current_date+10,current_date+12,1,0,$3,now(),now())''',
            request_id,
            prop["id"],
            room_type_id,
        )
        await conn.execute(
            '''INSERT INTO reservations (
                   id,"propertyId","requestId","bookingNumber",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt"
               ) VALUES ($1,$2,$3,$4,'GUARANTEED',current_date+10,current_date+12,1,0,1,now(),now())''',
            reservation_id,
            prop["id"],
            request_id,
            f"CI-IMPORT-{str(reservation_id)[:8]}",
        )
    finally:
        await conn.close()

    before = await snapshot_room(TARGET_CODE)
    blocked = run_import("--apply", expect_success=False)
    assert "Refusing physical-room apply while GUARANTEED/CHECKED_IN reservations exist" in (blocked.stdout + blocked.stderr)
    after = await snapshot_room(TARGET_CODE)
    assert after == before, "blocked apply changed room metadata/state"

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('DELETE FROM reservations WHERE id=$1', reservation_id)
        await conn.execute('DELETE FROM reservation_requests WHERE id=$1', request_id)
    finally:
        await conn.close()


def assert_canonical_metadata(actual: dict, canonical: dict[str, str]) -> None:
    assert actual["name"] == canonical["room_name"].strip()
    assert actual["buildingOrZone"] == clean(canonical.get("building_or_zone"))
    assert actual["floorLabel"] == clean(canonical.get("floor"))
    assert actual["bedConfiguration"] == clean(canonical.get("bed_configuration"))
    assert actual["areaLabel"] == clean(canonical.get("area_m2"))
    assert actual["notes"] == clean(canonical.get("notes"))


async def main() -> None:
    canonical = canonical_target()
    approval = json.loads(APPROVAL.read_text(encoding="utf-8"))
    actual_sha = hashlib.sha256(ROOMS_CSV.read_bytes()).hexdigest()
    assert approval["status"] == "OWNER_APPROVED"
    assert approval["room_count"] == 84
    assert approval["rooms_sha256"] == actual_sha

    baseline_invariants = await database_invariants()
    assert baseline_invariants["room_count"] == 84
    assert baseline_invariants["room_type_count"] == 12

    # 1. Clean baseline dry-run must be exactly a no-op.
    baseline_room_before = await snapshot_room(TARGET_CODE)
    dry = run_import()
    output = dry.stdout + dry.stderr
    assert "owner_approval=VERIFIED canonical_rooms=84" in output
    assert "desired_rooms=84 current_rooms=84" in output
    assert "added_codes=0 missing_codes=0 metadata_changes=0" in output
    assert "DRY RUN OK: approval verified; no database changes were made." in output
    baseline_room_after = await snapshot_room(TARGET_CODE)
    assert baseline_room_after == baseline_room_before, "baseline dry-run mutated room data"
    assert await database_invariants() == baseline_invariants, "baseline dry-run mutated database invariants"

    # 2. Corrupt physical metadata and runtime state. Dry-run must report metadata
    # differences but preserve all DB values.
    await corrupt_target_metadata()
    stale_before = await snapshot_room(TARGET_CODE)
    assert stale_before["operational_state"] == "DIRTY"
    dry_changed = run_import()
    changed_output = dry_changed.stdout + dry_changed.stderr
    assert "metadata_changes=1" in changed_output
    assert f"change {TARGET_CODE}:" in changed_output
    assert "operational_state" not in next(
        line for line in changed_output.splitlines() if line.startswith(f"change {TARGET_CODE}:")
    )
    stale_after_dry = await snapshot_room(TARGET_CODE)
    assert stale_after_dry == stale_before, "dry-run changed stale metadata or runtime state"

    # 3. Invalid approval checksum must fail closed before changing the database.
    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "bad-approval.json"
        bad = dict(approval)
        bad["rooms_sha256"] = "0" * 64
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        rejected = run_import("--approval", str(bad_path), "--apply", expect_success=False)
        rejected_output = rejected.stdout + rejected.stderr
        assert "owner approval verification failed" in rejected_output
        assert "rooms_sha256 does not match current" in rejected_output
    after_bad_approval = await snapshot_room(TARGET_CODE)
    assert after_bad_approval == stale_before, "bad approval changed database state"

    # 4. Active reservation safety barrier must block apply without mutation.
    await prove_no_active_lock_bypass()

    # 5. Approved apply repairs physical metadata transactionally while preserving
    # existing runtime operational state (DIRTY) and unrelated domain counts.
    invariants_before_apply = await database_invariants()
    applied = run_import("--apply")
    applied_output = applied.stdout + applied.stderr
    assert "APPLY OK: 84 owner-approved physical rooms verified; runtime operational state preserved." in applied_output
    repaired = await snapshot_room(TARGET_CODE)
    assert_canonical_metadata(repaired, canonical)
    assert repaired["operational_state"] == "DIRTY", "physical reconciliation overwrote runtime PMS state"

    invariants_after_apply = await database_invariants()
    assert invariants_after_apply["room_count"] == 84
    assert invariants_after_apply["room_type_count"] == 12
    for key in ("rate_count", "reservation_count", "payment_count", "inventory_count"):
        assert invariants_after_apply[key] == invariants_before_apply[key], (
            key,
            invariants_before_apply,
            invariants_after_apply,
        )

    final_dry = run_import()
    final_output = final_dry.stdout + final_dry.stderr
    assert "added_codes=0 missing_codes=0 metadata_changes=0" in final_output

    print(
        "PASS: owner-approved 84-room reconciliation dry-run/apply, checksum fail-closed, "
        "active-reservation guard, no-op diff, and runtime operational-state preservation"
    )


if __name__ == "__main__":
    asyncio.run(main())
