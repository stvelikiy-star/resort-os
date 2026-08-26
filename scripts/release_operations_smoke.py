#!/usr/bin/env python3
"""Development/staging HTTP smoke test for the hotel operations lifecycle.

Requires a running Resort Core and synthetic owner/maid accounts. It creates only
clearly marked RC task records and leaves the selected room CLEAN at the end.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = os.environ.get("CORE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ.get("RC_OWNER_USERNAME", "rc-owner")
OWNER_PASSWORD = os.environ.get("RC_OWNER_PASSWORD", "RC-Local-Only-Password-2026")
MAID_USERNAME = os.environ.get("RC_MAID_USERNAME", "rc-maid")
MAID_PASSWORD = os.environ.get("RC_MAID_PASSWORD", "RC-Maid-Local-Only-Password-2026")


def opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(client, method: str, path: str, payload=None, expected=(200, 201)):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    try:
        with client.open(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            if response.status not in expected:
                raise AssertionError(f"{method} {path}: expected {expected}, got {response.status}: {data}")
            return response.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        if exc.code not in expected:
            raise AssertionError(f"{method} {path}: expected {expected}, got {exc.code}: {data}") from exc
        return exc.code, data


def login(client, username: str, password: str):
    _, data = call(client, "POST", "/api/v1/auth/login", {"username": username, "password": password})
    return data


def room_state(owner, room_id: str) -> str:
    _, detail = call(owner, "GET", f"/api/v1/admin/rooms/{room_id}")
    return detail["room"]["operational_state"]


def main() -> int:
    if os.environ.get("APP_ENV", "development").lower() in {"prod", "production"}:
        print("ERROR: release_operations_smoke.py refuses production", file=sys.stderr)
        return 1

    owner = opener()
    maid = opener()
    owner_user = login(owner, OWNER_USERNAME, OWNER_PASSWORD)
    maid_user = login(maid, MAID_USERNAME, MAID_PASSWORD)
    assert owner_user["role"] in {"OWNER", "MANAGER"}, owner_user
    assert maid_user["role"] == "MAID", maid_user

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=1)).isoformat()
    query = urllib.parse.urlencode({"start": start, "end": end})
    _, grid = call(owner, "GET", f"/api/v1/pms/grid?{query}")
    rooms = [room for room in grid.get("rooms", []) if room.get("operational_state") != "TECH_BLOCK"]
    assert len(grid.get("rooms", [])) == 84, "PMS grid must contain 84 rooms"
    assert rooms, "No non-TECH_BLOCK room available for operations smoke"
    room = next((item for item in rooms if item.get("code") == "101"), rooms[0])
    room_id = room["id"]

    # Ensure the synthetic smoke starts from a known physical state without touching booking truth.
    call(owner, "PATCH", f"/api/v1/ops/rooms/{room_id}/state", {"state": "CLEAN"})

    _, created = call(
        owner,
        "POST",
        "/api/v1/ops/tasks",
        {
            "type": "HOUSEKEEPING",
            "room_id": room_id,
            "priority": "NORMAL",
            "title": f"RC_SMOKE housekeeping {room['code']}",
            "description": "Synthetic release-candidate operations lifecycle check",
            "source": "RC_LOCAL_CHECK",
        },
        expected=(201,),
    )
    task_id = created["id"]
    assert created["status"] == "OPEN"
    assert room_state(owner, room_id) == "DIRTY"

    # A manager cannot skip the workflow directly to DONE/CLEAN.
    code, rejected = call(
        owner,
        "PATCH",
        f"/api/v1/ops/tasks/{task_id}/status",
        {"status": "DONE"},
        expected=(409,),
    )
    assert code == 409
    assert rejected["detail"]["code"] == "INVALID_TASK_TRANSITION", rejected
    assert room_state(owner, room_id) == "DIRTY"

    # Maid claims the unassigned task and sends it to inspection.
    _, claimed = call(maid, "POST", f"/api/v1/ops/tasks/{task_id}/claim")
    assert claimed["status"] == "IN_PROGRESS"
    _, inspection = call(maid, "PATCH", f"/api/v1/ops/tasks/{task_id}/status", {"status": "IN_INSPECTION"})
    assert inspection["status"] == "IN_INSPECTION"
    assert room_state(owner, room_id) == "IN_INSPECTION"

    # Manager rejects inspection; room returns to DIRTY and the same maid can continue.
    _, rework = call(owner, "PATCH", f"/api/v1/ops/tasks/{task_id}/status", {"status": "IN_PROGRESS"})
    assert rework["status"] == "IN_PROGRESS"
    assert room_state(owner, room_id) == "DIRTY"

    _, inspection_again = call(maid, "PATCH", f"/api/v1/ops/tasks/{task_id}/status", {"status": "IN_INSPECTION"})
    assert inspection_again["status"] == "IN_INSPECTION"
    assert room_state(owner, room_id) == "IN_INSPECTION"

    _, done = call(owner, "PATCH", f"/api/v1/ops/tasks/{task_id}/status", {"status": "DONE"})
    assert done["status"] == "DONE"
    assert room_state(owner, room_id) == "CLEAN"

    _, history = call(owner, "GET", f"/api/v1/ops/tasks/{task_id}/history")
    transitions = [item for item in history.get("history", []) if item.get("action") == "STATUS_CHANGE"]
    assert len(transitions) >= 4, history

    print(f"PASS: operations lifecycle smoke · room {room['code']} · task {task_id}")
    print("FLOW: DIRTY -> IN_PROGRESS -> IN_INSPECTION -> DIRTY -> IN_INSPECTION -> CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
