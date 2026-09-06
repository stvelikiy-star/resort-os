import asyncio
import os
import secrets
import uuid

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
DATABASE_URL = os.environ["DATABASE_URL"].replace("?schema=public", "")


def expect(response: httpx.Response, status_code: int, context: str) -> dict:
    if response.status_code != status_code:
        raise AssertionError(
            f"{context}: expected HTTP {status_code}, got {response.status_code}: {response.text[:1000]}"
        )
    return response.json() if response.content else {}


def session(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)
    expect(client.post("/api/v1/auth/login", json={"username": username, "password": password}), 200, f"login {username}")
    return client


async def audit_counts(actions: list[str]) -> dict[str, int]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            '''SELECT action,count(*)::int AS count
               FROM audit_logs
               WHERE source IN ('RATE_MANAGEMENT','STAFF_MANAGEMENT')
                 AND action = ANY($1::text[])
               GROUP BY action''',
            actions,
        )
        return {row["action"]: row["count"] for row in rows}
    finally:
        await conn.close()


def generated_password(label: str) -> str:
    return f"{label}-{secrets.token_urlsafe(18)}-A9"


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    maid_username = f"mgmt-maid-{suffix}"
    manager_username = f"mgmt-manager-{suffix}"
    maid_password = generated_password("MaidStart")
    maid_new_password = generated_password("MaidNew")
    manager_password = generated_password("Manager")

    owner = session(OWNER_USERNAME, OWNER_PASSWORD)
    try:
        me = expect(owner.get("/api/v1/auth/me"), 200, "owner me")
        assert me["role"] == "OWNER"

        overview = expect(owner.get("/api/v1/admin/staff/overview"), 200, "staff overview")
        assert overview["can_manage_access"] is True
        assert "OWNER" not in overview["managed_roles"]
        owner_row = next(item for item in overview["staff"] if item["role"] == "OWNER")

        rates = expect(owner.get("/api/v1/admin/rates"), 200, "rate overview")
        assert len(rates["room_types"]) == 12
        assert len(rates["periods"]) == 48
        assert rates["rules"]["overlap_allowed"] is False
        assert rates["rules"]["existing_reservation_totals_rewritten"] is False
        assert rates["rules"]["delete_supported"] is False

        period = next(item for item in rates["periods"] if item["sale_status"] == "OPEN" and item["price_kgs"] > 0)
        original_price = period["price_kgs"]
        updated = expect(
            owner.patch(f"/api/v1/admin/rates/periods/{period['id']}", json={"price_kgs": original_price + 1}),
            200,
            "rate patch",
        )
        assert updated["price_kgs"] == original_price + 1

        refreshed = expect(owner.get("/api/v1/admin/rates"), 200, "rate refresh")
        persisted = next(item for item in refreshed["periods"] if item["id"] == period["id"])
        assert persisted["price_kgs"] == original_price + 1

        overlap = owner.post(
            "/api/v1/admin/rates/periods",
            json={
                "room_type_id": period["room_type_id"],
                "label": "CI overlapping rate",
                "valid_from": period["valid_from"][:10],
                "valid_to": period["valid_to"][:10],
                "price_kgs": max(1, original_price),
                "meal_included": period["meal_included"],
                "sale_status": "OPEN",
                "notes": "must fail closed",
            },
        )
        expect(overlap, 409, "overlap protection")
        restored = expect(
            owner.patch(f"/api/v1/admin/rates/periods/{period['id']}", json={"price_kgs": original_price}),
            200,
            "rate restore",
        )
        assert restored["price_kgs"] == original_price

        maid = expect(
            owner.post(
                "/api/v1/admin/staff",
                json={"username": maid_username, "display_name": "Management CI Maid", "password": maid_password, "role": "MAID"},
            ),
            201,
            "create maid",
        )
        assert maid["role"] == "MAID" and maid["active"] is True

        maid_client = session(maid_username, maid_password)
        try:
            assert expect(maid_client.get("/api/v1/auth/me"), 200, "maid me")["role"] == "MAID"
            changed = expect(
                owner.patch(
                    f"/api/v1/admin/staff/{maid['id']}",
                    json={"display_name": "Management CI Technician", "role": "TECHNICIAN", "password": maid_new_password},
                ),
                200,
                "change maid access",
            )
            assert changed["role"] == "TECHNICIAN"
            expect(maid_client.get("/api/v1/auth/me"), 401, "old session revoked")
        finally:
            maid_client.close()

        expect(
            httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"username": maid_username, "password": maid_password}, timeout=15.0),
            401,
            "old password rejected",
        )
        technician = session(maid_username, maid_new_password)
        try:
            assert expect(technician.get("/api/v1/auth/me"), 200, "new password login")["role"] == "TECHNICIAN"
        finally:
            technician.close()

        disabled = expect(owner.patch(f"/api/v1/admin/staff/{maid['id']}", json={"active": False}), 200, "disable staff")
        assert disabled["active"] is False
        expect(
            httpx.post(f"{BASE_URL}/api/v1/auth/login", json={"username": maid_username, "password": maid_new_password}, timeout=15.0),
            401,
            "disabled staff login",
        )

        manager = expect(
            owner.post(
                "/api/v1/admin/staff",
                json={"username": manager_username, "display_name": "Management CI Manager", "password": manager_password, "role": "MANAGER"},
            ),
            201,
            "create manager",
        )
        manager_client = session(manager_username, manager_password)
        try:
            expect(manager_client.get("/api/v1/admin/rates"), 200, "manager rate access")
            expect(
                manager_client.post(
                    "/api/v1/admin/staff",
                    json={"username": f"forbidden-{suffix}", "display_name": "Forbidden Staff", "password": generated_password("Denied"), "role": "MAID"},
                ),
                403,
                "manager staff mutation denied",
            )
        finally:
            manager_client.close()
        expect(owner.patch(f"/api/v1/admin/staff/{manager['id']}", json={"active": False}), 200, "disable manager")

        expect(owner.patch(f"/api/v1/admin/staff/{owner_row['id']}", json={"active": False}), 403, "owner account protection")

        counts = asyncio.run(audit_counts(["UPDATE_RATE_PERIOD", "CREATE_STAFF_USER", "UPDATE_STAFF_ACCESS"]))
        assert counts.get("UPDATE_RATE_PERIOD", 0) >= 2, counts
        assert counts.get("CREATE_STAFF_USER", 0) >= 2, counts
        assert counts.get("UPDATE_STAFF_ACCESS", 0) >= 3, counts

        final_rates = expect(owner.get("/api/v1/admin/rates"), 200, "final rate overview")
        assert len(final_rates["periods"]) == 48

        print("MANAGEMENT CONTROL VERIFIED")
        print("rates: 12 room types / 48 periods / update+restore / overlap fail-closed")
        print("staff: owner create / role+password rotation / session revoke / deactivate")
        print("RBAC: manager rates allowed; staff access mutation denied; owner account protected")
        print("audit: rate and staff security mutations recorded")
    finally:
        owner.close()


if __name__ == "__main__":
    main()
