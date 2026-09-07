#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"missing required file: {path}")
    return target.read_text(encoding="utf-8")


def rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def main() -> int:
    passed = 0

    def ok(condition: bool, label: str) -> None:
        nonlocal passed
        check(condition, label)
        passed += 1

    # 1) Historical demo must be fail-closed in the final management build.
    demo = read("apps/admin/app/demo/page.tsx")
    ok('from "next/navigation"' in demo, "admin demo imports Next fail-closed navigation")
    ok("notFound();" in demo, "admin demo route returns 404")
    ok('"use client"' not in demo, "admin demo is not a client-side bypass")
    for forbidden in ["Айбек", "Марина", "+996", "+7 9", "186 500", "NFC / пляжный терминал"]:
        ok(forbidden not in demo, f"admin demo no longer ships synthetic operational marker: {forbidden}")

    # 2) Admin authentication and UI role boundaries remain present.
    shell = read("apps/admin/components/AdminShell.tsx")
    for marker in [
        '/core/api/v1/auth/me',
        '/core/api/v1/auth/login',
        '/core/api/v1/auth/logout',
        'const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"])',
        'const isManager = ["OWNER", "MANAGER"].includes(user.role)',
        'const canUseReception = isManager || isReception',
        'const canUseOps = isManager || ["MAID", "TECHNICIAN"].includes(user.role)',
        'type="password"',
        'minLength={8}',
    ]:
        ok(marker in shell, f"admin auth/RBAC marker present: {marker}")

    # 3) Core auth security invariants.
    auth = read("services/api/app/auth.py")
    for marker in [
        'PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)',
        'hashlib.sha256(token.encode("utf-8")).hexdigest()',
        'Invalid username or password',
        'AUTH_LOGIN_PAIR_MAX_FAILURES',
        'AUTH_LOGIN_IP_MAX_FAILURES',
        'pg_advisory_lock',
        'row["property_code"] != PROPERTY_CODE',
        'require_roles(*allowed_roles: str)',
    ]:
        ok(marker in auth, f"Core auth invariant present: {marker}")

    # 4) Production environment must be secure-by-template and keep providers explicit.
    prod_env = read(".env.production.example")
    for marker in [
        "COOKIE_SECURE=true",
        "AUTH_TRUST_PROXY_HEADERS=true",
        "EXPECTED_ROOM_COUNT=84",
        "EXPECTED_ROOM_TYPE_COUNT=12",
        "REQUIRE_MIGRATION_HISTORY=true",
        "REQUIRE_RECENT_BACKUP=true",
        "POSTGRES_PASSWORD=CHANGE_ME_STRONG_DATABASE_PASSWORD",
        "AUTOMATION_SERVICE_KEY=CHANGE_ME_LONG_RANDOM_SERVICE_KEY_AT_LEAST_32_CHARS",
        "GREEN_API_WEBHOOK_SECRET=CHANGE_ME_LONG_RANDOM_WEBHOOK_SECRET",
    ]:
        ok(marker in prod_env, f"production env invariant present: {marker}")
    ok("N8N_IMAGE=n8nio/n8n:" in prod_env and "latest" not in prod_env, "n8n production image is pinned")
    ok("BOOTSTRAP_OWNER_PASSWORD=\n" in prod_env, "owner bootstrap password is not committed")

    # 5) Frozen release truth must remain internally consistent and not claim production GO.
    rc = json.loads(read("release/current-rc.json"))
    ok(rc["release_version"] == "0.62.0", "release version remains 0.62.0")
    ok(rc["status"] == "INTERNAL_RC_FROZEN_EXTERNAL_EVIDENCE_PENDING", "release remains internal RC")
    ok(len(rc["accepted_executable_head"]) == 40, "accepted executable is exact SHA")
    ok(rc["accepted_head_workflows"] == {"triggered": 21, "success": 21, "failures": 0}, "accepted executable workflow ledger is exact")
    ok(rc["migration_count"] == 22, "release migration count is 22")
    ok(rc["critical_constraint_count"] == 87, "release critical constraint count is 87")
    ok(rc["canonical_property_seed"] == {"rooms": 84, "room_categories": 12, "rate_rows": 48}, "canonical seed ledger is exact")
    ok(rc["external_beget_staging_verified"] is False, "external staging is not falsely marked verified")
    ok(rc["legacy_live_rollback_verified"] is False, "legacy rollback is not falsely marked verified")
    ok(rc["production_cutover_authorized"] is False, "production cutover remains fail-closed")

    # 6) Canonical room register data quality.
    room_rows = rows("data-intake/rooms.csv")
    ok(len(room_rows) == 84, "canonical room register has exactly 84 rows")
    codes = [r["room_code"].strip() for r in room_rows]
    ok(len(set(codes)) == 84, "room codes are unique")
    ok(all(code for code in codes), "room codes are non-empty")
    ok(all(r["room_name"].strip() for r in room_rows), "room names are non-empty")
    ok(all(int(r["capacity_adults"]) >= 1 for r in room_rows), "every room has positive adult capacity")
    room_types = {r["room_type"].strip() for r in room_rows}
    ok(len(room_types) == 12, "room register has exactly 12 room types")
    by_code = {r["room_code"].strip(): r for r in room_rows}
    ok("501" in by_code and "502" in by_code, "rooms 501 and 502 exist")
    ok(by_code["501"]["capacity_adults"] == "2", "room 501 is two-person inventory")
    ok(by_code["502"]["capacity_adults"] == "2", "room 502 is two-person inventory")

    # 7) Rate ledger: 12 categories x 4 contiguous/non-overlapping periods = 48 rows.
    rate_rows = rows("data-intake/rates.csv")
    ok(len(rate_rows) == 48, "rate ledger has exactly 48 rows")
    rate_types = {r["room_type"].strip() for r in rate_rows}
    ok(rate_types == room_types, "rate room types exactly match room register types")
    counts = Counter(r["room_type"].strip() for r in rate_rows)
    ok(set(counts.values()) == {4}, "each room type has exactly four rate periods")
    periods: dict[str, list[tuple[date, date]]] = defaultdict(list)
    zero_rows = 0
    for r in rate_rows:
        start = date.fromisoformat(r["valid_from"])
        end = date.fromisoformat(r["valid_to"])
        ok(start <= end, f"valid rate interval for {r['room_type']} {r['rate_name']}")
        price = int(r["price_kgs"])
        ok(price >= 0, f"non-negative rate for {r['room_type']} {r['rate_name']}")
        if price == 0:
            zero_rows += 1
            ok("DO NOT interpret as free" in r["notes"], f"zero rate is explicitly fail-closed for {r['room_type']}")
        periods[r["room_type"].strip()].append((start, end))
    ok(zero_rows > 0, "zero/off-season rows are intentionally represented and guarded")
    for room_type, values in periods.items():
        values.sort()
        for previous, current in zip(values, values[1:]):
            ok(previous[1] < current[0], f"rate periods do not overlap for {room_type}")

    # 8) Kitchen commercial authority remains separated from dining operations.
    kitchen_ui = read("apps/staff/components/KitchenAdminV2.tsx")
    kitchen_entry = read("apps/staff/components/KitchenEntry.tsx")
    kitchen_core = read("services/api/app/kitchen_menu_management.py")
    ok('import KitchenAdminV2 from "./KitchenAdminV2"' in kitchen_entry, "Kitchen V2 is mounted")
    ok('import KitchenAdmin from "./KitchenAdmin"' not in kitchen_entry, "legacy Kitchen admin is not mounted")
    ok("Загрузить тестовое меню" not in kitchen_ui, "production Kitchen has no demo bootstrap")
    ok('user?.role === "OWNER" || user?.role === "MANAGER"' in kitchen_ui, "Kitchen menu UI is manager-owned")
    ok('manager_access = require_roles("OWNER", "MANAGER")' in kitchen_core, "Kitchen menu Core mutation is manager-owned")

    # 9) External acceptance remains intentionally fail-closed even though VPS is deferred.
    staging = read("scripts/external_staging_acceptance.py")
    for marker in [
        '"legacy_rollback_gate"',
        '"deployment_release_linkage"',
        '"external_public_truth"',
        '"staging_business_acceptance"',
        '"production_monitoring"',
        '"production_target_allowed": False',
        'parsed.scheme != "https"',
        'parsed.scheme != "wss"',
        '"staging" not in parsed.hostname.lower()',
        'output directory must be empty',
        'contains_credentials": False',
        'changes_dns": False',
    ]:
        ok(marker in staging, f"external staging fail-closed marker present: {marker}")
    sequence = [
        staging.index('"legacy_rollback_gate"'),
        staging.index('"deployment_release_linkage"'),
        staging.index('"external_public_truth"'),
        staging.index('"staging_business_acceptance"'),
        staging.index('"production_monitoring"'),
    ]
    ok(sequence == sorted(sequence), "external acceptance gates execute in strict safety order")

    # This guard deliberately exceeds the previous 70-check final acceptance when combined.
    ok(passed >= 100, f"internal hardening suite unexpectedly small: {passed}")
    print(f"INTERNAL_HARDENING_PASS checks={passed}")
    print("BOUNDARY: management/admin/staff/Core only; apps/web is frozen; Beget/VPS deferred by owner")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError) as exc:
        print(f"INTERNAL_HARDENING_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
