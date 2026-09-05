#!/usr/bin/env python3
"""Smoke check for the unified Three Crowns public-site / CRM / PMS / CMS contour.

Assumes Resort Core is already running, schema/sql modules are applied, Three Crowns
seed is loaded and a temporary OWNER account is available through environment vars.
Never use real guest/payment data in this check.
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER = os.environ.get("SMOKE_OWNER_USERNAME") or os.environ.get("BOOTSTRAP_OWNER_USERNAME")
PASSWORD = os.environ.get("SMOKE_OWNER_PASSWORD") or os.environ.get("BOOTSTRAP_OWNER_PASSWORD")

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(path: str, *, method: str = "GET", body=None, authenticated: bool = False, allow_error: bool = False):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    client = opener if authenticated else urllib.request.build_opener()
    try:
        with client.open(req, timeout=10) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            decoded = json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            decoded = {"raw": payload}
        if allow_error:
            return exc.code, decoded
        raise RuntimeError(f"{method} {path}: HTTP {exc.code} {payload}") from exc


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> int:
    status, ready = request("/ready")
    check(status == 200, "Core readiness")
    check(ready.get("property") == "THREE_CROWNS", "Three Crowns property context")
    check(ready.get("room_count") == 84 and ready.get("room_type_count") == 12, "Canonical 84 rooms / 12 categories")

    status, public_before = request("/api/v1/site/content?locale=ru")
    check(status == 200 and isinstance(public_before.get("content"), dict), "Public CMS content returns an object")
    original_title = public_before["content"].get("hero", {}).get("title")
    check(bool(original_title), "Public CMS fallback/published hero is populated")

    if not OWNER or not PASSWORD:
        raise RuntimeError("Set SMOKE_OWNER_USERNAME/SMOKE_OWNER_PASSWORD or bootstrap owner credentials")
    status, login = request("/api/v1/auth/login", method="POST", body={"username": OWNER, "password": PASSWORD}, authenticated=True)
    check(status == 200 and login.get("role") in {"OWNER", "MANAGER"}, "Manager authentication")

    status, admin_content = request("/api/v1/admin/site/content", authenticated=True)
    check(status == 200 and len(admin_content.get("items", [])) == 3, "CMS admin exposes RU/KG/EN")

    ru_item = next(item for item in admin_content["items"] if item["locale"] == "ru")

    forbidden = json.loads(json.dumps(ru_item["draft"], ensure_ascii=False))
    forbidden.setdefault("booking", {})["intro"] = "Для подтверждения нужна 30% предоплата."
    status, rejected = request(
        "/api/v1/admin/site/content/ru/draft",
        method="PUT",
        body={"content": forbidden},
        authenticated=True,
        allow_error=True,
    )
    check(status == 422 and rejected.get("detail", {}).get("code") == "PUBLIC_CONTENT_TRUTH_VIOLATION", "CMS rejects fixed 30% prepayment claim")

    forbidden_amenity = json.loads(json.dumps(ru_item["draft"], ensure_ascii=False))
    forbidden_amenity.setdefault("advantages", {})["intro"] = "На территории работает сауна."
    status, rejected = request(
        "/api/v1/admin/site/content/ru/draft",
        method="PUT",
        body={"content": forbidden_amenity},
        authenticated=True,
        allow_error=True,
    )
    check(status == 422 and rejected.get("detail", {}).get("code") == "PUBLIC_CONTENT_TRUTH_VIOLATION", "CMS rejects uncanonicalized sauna claim")

    unknown_schema = json.loads(json.dumps(ru_item["draft"], ensure_ascii=False))
    unknown_schema["unreviewed_section"] = {"copy": "test"}
    status, rejected = request(
        "/api/v1/admin/site/content/ru/draft",
        method="PUT",
        body={"content": unknown_schema},
        authenticated=True,
        allow_error=True,
    )
    check(status == 422 and rejected.get("detail", {}).get("code") == "PUBLIC_CONTENT_UNKNOWN_SECTION", "CMS rejects unknown public schema sections")

    draft = json.loads(json.dumps(ru_item["draft"], ensure_ascii=False))
    marker = "[SMOKE] Три Короны CMS"
    draft.setdefault("hero", {})["title"] = marker
    status, saved = request("/api/v1/admin/site/content/ru/draft", method="PUT", body={"content": draft}, authenticated=True)
    check(status == 200 and saved.get("draft", {}).get("hero", {}).get("title") == marker, "CMS draft save")

    status, public_draft = request("/api/v1/site/content?locale=ru")
    check(public_draft.get("content", {}).get("hero", {}).get("title") != marker, "Draft is not public before publish")

    status, published = request("/api/v1/admin/site/content/ru/publish", method="POST", authenticated=True)
    check(status == 200 and published.get("content", {}).get("hero", {}).get("title") == marker, "CMS publish")
    status, public_after = request("/api/v1/site/content?locale=ru")
    check(public_after.get("content", {}).get("hero", {}).get("title") == marker, "Public site sees published CMS version")

    restore = json.loads(json.dumps(draft, ensure_ascii=False))
    restore.setdefault("hero", {})["title"] = original_title
    request("/api/v1/admin/site/content/ru/draft", method="PUT", body={"content": restore}, authenticated=True)
    request("/api/v1/admin/site/content/ru/publish", method="POST", authenticated=True)
    status, restored = request("/api/v1/site/content?locale=ru")
    check(restored.get("content", {}).get("hero", {}).get("title") == original_title, "CMS smoke restores original content")

    tomorrow = date.today() + timedelta(days=40)
    checkout = tomorrow + timedelta(days=2)
    status, availability = request(
        f"/api/v1/booking/check-availability?check_in={tomorrow.isoformat()}&check_out={checkout.isoformat()}&adults=2&children=0"
    )
    check(status == 200 and isinstance(availability.get("results"), list), "Public availability uses Core")

    status, created = request(
        "/api/v1/booking/requests",
        method="POST",
        body={
            "guest_name": "Integration Smoke Guest",
            "phone": "+996000000001",
            "check_in": tomorrow.isoformat(),
            "check_out": checkout.isoformat(),
            "adults": 2,
            "children": 0,
            "source": "INTEGRATION_SMOKE",
        },
    )
    check(status in (200, 201) and created.get("is_reservation") is False and created.get("status") == "NEW", "Website submission creates CRM request, not reservation")

    status, requests = request("/api/v1/admin/booking/requests?limit=100", authenticated=True)
    request_id = created.get("id")
    items = requests.get("items", requests if isinstance(requests, list) else [])
    check(any(str(item.get("id")) == str(request_id) for item in items), "Website request is visible in manager CRM")

    status, grid = request(
        f"/api/v1/pms/grid?start={tomorrow.isoformat()}&end={(checkout + timedelta(days=5)).isoformat()}",
        authenticated=True,
    )
    check(status == 200 and isinstance(grid.get("rooms"), list), "PMS chessboard reads the same Core inventory")

    today = date.today()
    snapshot_end = today + timedelta(days=31)
    status, snapshot = request(
        f"/api/v1/admin/pms/control-snapshot?start={today.isoformat()}&end={snapshot_end.isoformat()}",
        authenticated=True,
    )
    check(status == 200 and snapshot.get("complete") is True, "V9 manager control snapshot is fail-closed complete")
    check(snapshot.get("summary", {}).get("room_count") == 84 and len(snapshot.get("rooms", [])) == 84, "V9 snapshot covers all 84 physical rooms")
    check(isinstance(snapshot.get("reservations"), list) and isinstance(snapshot.get("tasks"), list), "V9 snapshot includes reservations and operational tasks")
    check(all(item.get("status") in {"GUARANTEED", "CHECKED_IN"} for item in snapshot.get("reservations", [])), "V9 active reservation projection uses canonical lifecycle statuses")

    active_pairs = [
        (task.get("room_id"), task.get("type"))
        for task in snapshot.get("tasks", [])
        if task.get("room_id") and task.get("type") in {"HOUSEKEEPING", "MAINTENANCE"}
    ]
    check(len(active_pairs) == len(set(active_pairs)), "No duplicate active housekeeping/maintenance pair in V9 snapshot")

    print("\nUnified Site/PMS/CRM/CMS/V9 smoke check completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
