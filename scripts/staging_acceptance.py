#!/usr/bin/env python3
"""Full staging acceptance gate for Three Crowns Resort OS.

Run only against an isolated staging database and synthetic credentials.
The script intentionally creates synthetic operational tasks and a website CRM request.
"""

import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:18000").rstrip("/")
OWNER = os.environ.get("SMOKE_OWNER_USERNAME")
OWNER_PASSWORD = os.environ.get("SMOKE_OWNER_PASSWORD")
MAID = os.environ.get("SMOKE_MAID_USERNAME")
MAID_PASSWORD = os.environ.get("SMOKE_MAID_PASSWORD")
TECH = os.environ.get("SMOKE_TECHNICIAN_USERNAME")
TECH_PASSWORD = os.environ.get("SMOKE_TECHNICIAN_PASSWORD")


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path: str, *, method: str = "GET", body=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            BASE + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=15) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw}
            return exc.code, payload

    def login(self, username: str, password: str):
        status, body = self.request(
            "/api/v1/auth/login",
            method="POST",
            body={"username": username, "password": password},
        )
        if status != 200:
            raise AssertionError(f"login failed for {username}: HTTP {status} {body}")
        return body


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def required_env():
    missing = [
        name
        for name, value in [
            ("SMOKE_OWNER_USERNAME", OWNER),
            ("SMOKE_OWNER_PASSWORD", OWNER_PASSWORD),
            ("SMOKE_MAID_USERNAME", MAID),
            ("SMOKE_MAID_PASSWORD", MAID_PASSWORD),
            ("SMOKE_TECHNICIAN_USERNAME", TECH),
            ("SMOKE_TECHNICIAN_PASSWORD", TECH_PASSWORD),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError("Missing staging smoke credentials: " + ", ".join(missing))


def create_task(owner: Client, *, task_type: str, room_id: str, assigned_to_id: str, title: str):
    status, body = owner.request(
        "/api/v1/ops/tasks",
        method="POST",
        body={
            "type": task_type,
            "room_id": room_id,
            "priority": "HIGH",
            "title": title,
            "description": "Synthetic staging acceptance task. Safe to ignore outside staging.",
            "assigned_to_id": assigned_to_id,
            "source": "STAGING_ACCEPTANCE",
        },
    )
    check(status == 201 and body.get("id"), f"create assigned {task_type} task")
    return body["id"]


def claim(client: Client, task_id: str, label: str):
    status, body = client.request(f"/api/v1/ops/tasks/{task_id}/claim", method="POST")
    check(status == 200 and body.get("status") == "IN_PROGRESS", label)


def main() -> int:
    required_env()

    # Reuse the site/CMS/CRM/PMS smoke first. It restores CMS after itself.
    env = dict(os.environ)
    env["CORE_API_URL"] = BASE
    print("\n== Unified site/PMS/CRM/CMS smoke ==")
    subprocess.run([sys.executable, "scripts/site_pms_cms_smoke.py"], env=env, check=True)

    owner = Client()
    owner_user = owner.login(OWNER, OWNER_PASSWORD)
    check(owner_user.get("role") in {"OWNER", "MANAGER"}, "owner/manager staging session")

    today = date.today()
    report_to = today + timedelta(days=30)
    query = urllib.parse.urlencode({"from_date": today.isoformat(), "to_date": report_to.isoformat()})
    status, report = owner.request(f"/api/v1/admin/reports/overview?{query}")
    check(status == 200, "analytics report endpoint")
    check(report.get("kpi", {}).get("room_count") == 84, "analytics sees canonical 84 rooms")
    check(len(report.get("room_types", [])) == 12, "analytics sees canonical 12 categories")
    check(report.get("truth", {}).get("source_of_truth") == "RESORT_CORE", "analytics declares Resort Core truth")

    status, staff = owner.request("/api/v1/admin/staff/overview")
    check(status == 200, "staff overview endpoint")
    staff_items = staff.get("staff", [])
    maid_row = next((item for item in staff_items if item.get("username") == MAID), None)
    tech_row = next((item for item in staff_items if item.get("username") == TECH), None)
    check(maid_row and maid_row.get("role") == "MAID", "staging maid exists")
    check(tech_row and tech_row.get("role") == "TECHNICIAN", "staging technician exists")

    start = today.isoformat()
    end = (today + timedelta(days=14)).isoformat()
    status, snapshot = owner.request(f"/api/v1/admin/pms/control-snapshot?start={start}&end={end}")
    check(status == 200 and snapshot.get("complete") is True, "PMS control snapshot")
    rooms = snapshot.get("rooms", [])
    active_task_rooms = {item.get("room_id") for item in snapshot.get("tasks", []) if item.get("room_id")}
    active_reservation_rooms = {item.get("room_id") for item in snapshot.get("reservations", []) if item.get("room_id")}
    candidates = [
        room for room in rooms
        if room.get("id") not in active_task_rooms and room.get("id") not in active_reservation_rooms
    ]
    check(len(candidates) >= 2, "two safe rooms available for synthetic staff lifecycle")
    housekeeping_room, maintenance_room = candidates[0], candidates[1]

    housekeeping_task_id = create_task(
        owner,
        task_type="HOUSEKEEPING",
        room_id=housekeeping_room["id"],
        assigned_to_id=maid_row["id"],
        title=f"[STAGING] Уборка № {housekeeping_room['code']}",
    )
    maintenance_task_id = create_task(
        owner,
        task_type="MAINTENANCE",
        room_id=maintenance_room["id"],
        assigned_to_id=tech_row["id"],
        title=f"[STAGING] Ремонт № {maintenance_room['code']}",
    )

    maid_client = Client()
    maid_user = maid_client.login(MAID, MAID_PASSWORD)
    check(maid_user.get("role") == "MAID", "maid login")
    claim(maid_client, housekeeping_task_id, "maid claims assigned housekeeping")
    status, body = maid_client.request(
        f"/api/v1/ops/tasks/{housekeeping_task_id}/complete-report",
        method="POST",
        body={
            "summary": "Staging housekeeping completed and ready for inspection.",
            "checklist": [
                {"code": "BED_LINEN", "label": "Кровать и бельё", "done": True},
                {"code": "BATHROOM", "label": "Санузел", "done": True},
                {"code": "SURFACES", "label": "Пол и поверхности", "done": True},
                {"code": "AMENITIES", "label": "Комплектация номера", "done": True},
                {"code": "FINAL_CHECK", "label": "Финальная проверка", "done": True},
            ],
            "evidence_urls": [],
        },
    )
    check(status == 200 and body.get("status") == "IN_INSPECTION", "maid submits audited housekeeping report")
    check(body.get("room_state") in {"IN_INSPECTION", "TECH_BLOCK"}, "housekeeping transitions room to inspection unless tech-blocked")

    status, body = owner.request(
        f"/api/v1/ops/tasks/{housekeeping_task_id}/status",
        method="PATCH",
        body={"status": "DONE"},
    )
    check(status == 200, "manager accepts housekeeping inspection")

    tech_client = Client()
    tech_user = tech_client.login(TECH, TECH_PASSWORD)
    check(tech_user.get("role") == "TECHNICIAN", "technician login")
    claim(tech_client, maintenance_task_id, "technician claims assigned maintenance")
    status, body = tech_client.request(
        f"/api/v1/ops/tasks/{maintenance_task_id}/complete-report",
        method="POST",
        body={
            "summary": "Staging maintenance completed; room released to housekeeping.",
            "checklist": [],
            "evidence_urls": [],
        },
    )
    check(status == 200 and body.get("status") == "DONE", "technician submits audited maintenance report")
    check(body.get("room_state") == "DIRTY", "completed maintenance releases room to DIRTY")
    check(bool(body.get("housekeeping_task_id")), "completed maintenance creates/reuses housekeeping task")

    status, history = owner.request(f"/api/v1/ops/tasks/{maintenance_task_id}/history")
    check(status == 200, "task history endpoint after staff report")
    actions = {item.get("action") for item in history.get("history", [])}
    check("COMPLETE_WITH_REPORT" in actions, "completion report is present in audit trail")

    print("\nSTAGING ACCEPTANCE PASSED")
    print(f"Core: {BASE}")
    print(f"Synthetic housekeeping room: {housekeeping_room['code']}")
    print(f"Synthetic maintenance room: {maintenance_room['code']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STAGING ACCEPTANCE FAILED: {exc}", file=sys.stderr)
        raise
