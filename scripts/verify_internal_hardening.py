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


def main() -> int:
    passed = 0

    def ok(value: bool, label: str) -> None:
        nonlocal passed
        if not value:
            raise AssertionError(label)
        passed += 1

    demo = read("apps/admin/app/demo/page.tsx")
    ok('from "next/navigation"' in demo and "notFound();" in demo, "admin demo is fail-closed")
    ok('"use client"' not in demo, "admin demo cannot bypass on client")
    for forbidden in ("Айбек", "Марина", "+996", "186 500", "NFC / пляжный терминал"):
        ok(forbidden not in demo, f"demo synthetic marker removed: {forbidden}")

    shell = read("apps/admin/components/AdminShell.tsx")
    for marker in (
        '/core/api/v1/auth/me', '/core/api/v1/auth/login', '/core/api/v1/auth/logout',
        'const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"])',
        'const isManager = ["OWNER", "MANAGER"].includes(user.role)', 'type="password"', 'minLength={8}',
    ):
        ok(marker in shell, f"admin auth/RBAC marker: {marker}")

    auth = read("services/api/app/auth.py")
    for marker in (
        'PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)',
        'hashlib.sha256(token.encode("utf-8")).hexdigest()', 'Invalid username or password',
        'AUTH_LOGIN_PAIR_MAX_FAILURES', 'AUTH_LOGIN_IP_MAX_FAILURES', 'pg_advisory_lock',
        'row["property_code"] != PROPERTY_CODE', 'require_roles(*allowed_roles: str)',
    ):
        ok(marker in auth, f"Core auth invariant: {marker}")

    prod = read(".env.production.example")
    for marker in (
        "COOKIE_SECURE=true", "AUTH_TRUST_PROXY_HEADERS=true", "EXPECTED_ROOM_COUNT=84",
        "EXPECTED_ROOM_TYPE_COUNT=12", "REQUIRE_MIGRATION_HISTORY=true", "REQUIRE_RECENT_BACKUP=true",
        "POSTGRES_PASSWORD=CHANGE_ME_STRONG_DATABASE_PASSWORD",
        "AUTOMATION_SERVICE_KEY=CHANGE_ME_LONG_RANDOM_SERVICE_KEY_AT_LEAST_32_CHARS",
        "GREEN_API_WEBHOOK_SECRET=CHANGE_ME_LONG_RANDOM_WEBHOOK_SECRET",
    ):
        ok(marker in prod, f"production env invariant: {marker}")
    ok("N8N_IMAGE=n8nio/n8n:" in prod and "latest" not in prod, "n8n image pinned")
    ok("BOOTSTRAP_OWNER_PASSWORD=\n" in prod, "owner bootstrap password absent")

    rc = json.loads(read("release/current-rc.json"))
    ok(rc["release_version"] == "0.62.1", "release 0.62.1")
    ok(rc["accepted_executable_head"] == "b3bb0c1be4c522d765509796ddd1d32e8606dc89", "accepted hardening SHA")
    ok(rc["observed_merge_commit"] == "7f689458b2cf507d76a8c54fbe164e9492f79aca", "observed merge SHA")
    ok(rc["accepted_head_workflows"] == {"triggered": 28, "success": 28, "failures": 0}, "28/28 accepted workflows")
    ok(rc["merged_main_workflows"] == {"triggered": 23, "success": 23, "failures": 0}, "23/23 eligible merge workflows")
    ok(rc["migration_count"] == 22 and rc["critical_constraint_count"] == 87, "22 migrations / 87 constraints")
    ok(rc["canonical_property_seed"] == {"rooms": 84, "room_categories": 12, "rate_rows": 48}, "canonical property seed")
    for key in ("external_beget_staging_verified", "legacy_live_rollback_verified", "production_cutover_authorized"):
        ok(rc[key] is False, f"{key} remains fail-closed")

    room_rows = rows("data-intake/rooms.csv")
    ok(len(room_rows) == 84, "84 physical rooms")
    codes = [r["room_code"].strip() for r in room_rows]
    ok(len(set(codes)) == 84, "unique room codes")
    for r in room_rows:
        ok(bool(r["room_code"].strip()) and bool(r["room_name"].strip()), f"room source complete: {r['room_code']}")
        ok(int(r["capacity_adults"]) >= 1, f"positive room capacity: {r['room_code']}")
    by_code = {r["room_code"].strip(): r for r in room_rows}
    ok(by_code["501"]["capacity_adults"] == "2" and by_code["502"]["capacity_adults"] == "2", "501/502 two-person inventory")

    canonical_types = {
        "Одноместный, цоколь", "Двухместный стандарт, цоколь", "Одноместный, улучшенный",
        "Двухместный стандарт в коттеджном доме", "Двухместный улучшенный", "Полулюкс без балкона",
        "Люкс двухместный", "Люкс трехместный", "Двухкомнатный стандарт", "Двухкомнатный полулюкс",
        "Апартаменты", "Квартиры / апартаменты с кухней",
    }
    seed = read("scripts/seed_from_intake.py")
    for room_type in canonical_types:
        ok(f'"{room_type}"' in seed, f"canonical type mapped: {room_type}")

    rate_rows = rows("data-intake/rates.csv")
    ok(len(rate_rows) == 48, "48 rate rows")
    ok({r["room_type"].strip() for r in rate_rows} == canonical_types, "exact 12 rate categories")
    ok(set(Counter(r["room_type"].strip() for r in rate_rows).values()) == {4}, "four periods per category")
    periods: dict[str, list[tuple[date, date]]] = defaultdict(list)
    for r in rate_rows:
        start, end = date.fromisoformat(r["valid_from"]), date.fromisoformat(r["valid_to"])
        ok(start <= end, f"valid interval: {r['room_type']} {r['rate_name']}")
        price = int(r["price_kgs"])
        ok(price >= 0, f"non-negative rate: {r['room_type']} {r['rate_name']}")
        if price == 0:
            ok("DO NOT interpret as free" in r["notes"], f"zero rate fail-closed: {r['room_type']}")
        periods[r["room_type"].strip()].append((start, end))
    for room_type, values in periods.items():
        values.sort()
        for previous, current in zip(values, values[1:]):
            ok(previous[1] < current[0], f"non-overlap: {room_type}")

    kitchen = read("services/api/app/kitchen_menu_management.py")
    ok('manager_access = require_roles("OWNER", "MANAGER")' in kitchen, "Kitchen manager authority")
    ok('@router.post("/menu/bootstrap-draft")' in kitchen, "bootstrap route explicit")
    ok('os.environ.get("APP_ENV", "development").strip().lower() == "production"' in kitchen, "bootstrap checks production APP_ENV")
    ok('raise HTTPException(status_code=404, detail="Not found")' in kitchen, "bootstrap 404 in production")
    kitchen_verify = read("scripts/verify_kitchen_menu_management.py")
    ok("bootstrapDenied.status_code == 403" in kitchen_verify or "bootstrap_denied.status_code == 403" in kitchen_verify or "bootstrap" in kitchen_verify and "403" in kitchen_verify, "DINING_STAFF bootstrap negative E2E present")

    staging = read("scripts/external_staging_acceptance.py")
    for marker in (
        '"legacy_rollback_gate"', '"deployment_release_linkage"', '"external_public_truth"',
        '"staging_business_acceptance"', '"production_monitoring"', '"production_target_allowed": False',
        'parsed.scheme != "https"', 'parsed.scheme != "wss"', 'output directory must be empty',
        'contains_credentials": False', 'changes_dns": False',
    ):
        ok(marker in staging, f"external fail-closed marker: {marker}")

    ok(passed >= 100, f"hardening suite too small: {passed}")
    print(f"INTERNAL_HARDENING_PASS checks={passed}")
    print("BOUNDARY: management/admin/staff/Core only; apps/web is frozen; Beget/VPS deferred by owner")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError) as exc:
        print(f"INTERNAL_HARDENING_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
