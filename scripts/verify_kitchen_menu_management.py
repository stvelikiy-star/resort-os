import asyncio
import os
import uuid

import asyncpg
import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
DINING_USERNAME = os.environ["KITCHEN_MENU_DINING_USERNAME"]
DINING_PASSWORD = os.environ["KITCHEN_MENU_DINING_PASSWORD"]


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


async def login(username: str, password: str) -> httpx.AsyncClient:
    client = httpx.AsyncClient(base_url=BASE, timeout=20)
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    check(response.status_code == 200, f"login failed for {username}: {response.status_code} {response.text}")
    return client


async def main() -> None:
    code = f"CI_MENU_{uuid.uuid4().hex[:8].upper()}"
    conn = await asyncpg.connect(DB)
    owner = await login(OWNER_USERNAME, OWNER_PASSWORD)
    dining = await login(DINING_USERNAME, DINING_PASSWORD)
    try:
        created = await owner.post(
            "/api/v1/kitchen/menu",
            json={"code": code, "category": "MAIN", "name_ru": "CI блюдо", "price_kgs": 321, "is_active": True, "is_draft": True},
        )
        check(created.status_code == 201, f"owner create failed: {created.status_code} {created.text}")
        item = created.json()
        check(item["code"] == code and item["is_draft"] is True, "new item must be a draft")

        denied_create = await dining.post(
            "/api/v1/kitchen/menu",
            json={"code": f"{code}_NO", "category": "MAIN", "name_ru": "Forbidden", "price_kgs": 1},
        )
        check(denied_create.status_code == 403, f"DINING_STAFF create must be 403, got {denied_create.status_code}")

        denied_patch = await dining.patch(f"/api/v1/kitchen/menu/{item['id']}", json={"price_kgs": 999})
        check(denied_patch.status_code == 403, f"DINING_STAFF patch must be 403, got {denied_patch.status_code}")

        published = await owner.patch(f"/api/v1/kitchen/menu/{item['id']}", json={"is_draft": False, "price_kgs": 333})
        check(published.status_code == 200, f"owner publish failed: {published.text}")
        check(published.json()["is_draft"] is False and published.json()["price_kgs"] == 333, "publish/price not persisted")

        menu = await dining.get("/api/v1/kitchen/menu")
        check(menu.status_code == 200, f"DINING_STAFF must retain menu read access: {menu.text}")
        visible = next((row for row in menu.json()["items"] if row["id"] == item["id"]), None)
        check(visible is not None and visible["price_kgs"] == 333, "published menu not readable by dining staff")

        audit_count = await conn.fetchval(
            '''SELECT count(*) FROM audit_logs WHERE resource='KitchenMenuItem' AND "resourceId"=$1
               AND action IN ('CREATE_MENU_ITEM','UPDATE_MENU_ITEM') AND result='SUCCESS' ''',
            item["id"],
        )
        check(audit_count >= 2, f"expected menu audit entries, got {audit_count}")
        print("KITCHEN MENU MANAGEMENT E2E: PASS")
    finally:
        await owner.aclose()
        await dining.aclose()
        await conn.execute('DELETE FROM kitchen_menu_items WHERE code=$1', code)
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
