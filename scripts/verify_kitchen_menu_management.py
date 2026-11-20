import asyncio
import os
import uuid

import asyncpg
import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
COOK_USERNAME = os.environ.get("KITCHEN_MENU_COOK_USERNAME", os.environ["KITCHEN_MENU_DINING_USERNAME"])
COOK_PASSWORD = os.environ.get("KITCHEN_MENU_COOK_PASSWORD", os.environ["KITCHEN_MENU_DINING_PASSWORD"])


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
    cook = await login(COOK_USERNAME, COOK_PASSWORD)
    try:
        denied_bootstrap = await cook.post("/api/v1/kitchen/menu/bootstrap-draft")
        check(
            denied_bootstrap.status_code == 403,
            f"COOK draft bootstrap must be 403, got {denied_bootstrap.status_code}: {denied_bootstrap.text}",
        )

        created = await owner.post(
            "/api/v1/kitchen/menu",
            json={
                "code": code,
                "category": "MAIN",
                "name_ru": "CI блюдо",
                "name_kg": "CI тамагы",
                "name_kz": "CI тағамы",
                "name_en": "CI dish",
                "price_kgs": 321,
                "is_active": True,
                "is_draft": True,
            },
        )
        check(created.status_code == 201, f"owner create failed: {created.status_code} {created.text}")
        item = created.json()
        check(item["code"] == code and item["is_draft"] is True, "new item must be a draft")
        check(
            item["name_ru"] == "CI блюдо"
            and item["name_kg"] == "CI тамагы"
            and item["name_kz"] == "CI тағамы"
            and item["name_en"] == "CI dish",
            "multilingual menu names were not persisted",
        )

        denied_create = await cook.post(
            "/api/v1/kitchen/menu",
            json={
                "code": f"{code}_NO",
                "category": "MAIN",
                "name_ru": "Forbidden",
                "name_kg": "Тыюу салынган",
                "name_kz": "Тыйым салынған",
                "name_en": "Forbidden",
                "price_kgs": 1,
            },
        )
        check(denied_create.status_code == 403, f"COOK create must be 403, got {denied_create.status_code}")

        denied_patch = await cook.patch(f"/api/v1/kitchen/menu/{item['id']}", json={"price_kgs": 999})
        check(denied_patch.status_code == 403, f"COOK patch must be 403, got {denied_patch.status_code}")

        published = await owner.patch(f"/api/v1/kitchen/menu/{item['id']}", json={"is_draft": False, "price_kgs": 333})
        check(published.status_code == 200, f"owner publish failed: {published.text}")
        check(published.json()["is_draft"] is False and published.json()["price_kgs"] == 333, "publish/price not persisted")

        menu = await cook.get("/api/v1/kitchen/menu")
        check(menu.status_code == 200, f"COOK draft list failed: {menu.text}")
        check(all(row["is_draft"] and not row["is_active"] for row in menu.json()["items"]),
              "COOK author list must contain inactive drafts only")

        draft_code = code + "_COOK"
        draft = await cook.post("/api/v1/kitchen/menu", json={
            "code": draft_code, "category": "MAIN", "name_ru": "Черновик", "name_kg": "Долбоор",
            "name_kz": "Нобай", "name_en": "Draft", "price_kgs": 0,
            "is_active": False, "is_draft": True,
        })
        check(draft.status_code == 201, draft.text)
        draft_id = draft.json()["id"]
        path = f"/api/v1/kitchen/menu/{draft_id}"
        edited = await cook.patch(path, json={"name_ru": "Исправленный черновик"})
        check(edited.status_code == 200, edited.text)
        for change in ({"price_kgs": 5}, {"is_active": True}, {"is_draft": False}):
            check((await cook.patch(path, json=change)).status_code == 403, "COOK publication/price bypass")
        recipe = {"expected_version": 0, "status": "DRAFT", "is_sample": True,
                  "ingredients": [{"name": "Тестовый рис", "unit": "KG", "quantity_per_portion": "0.1"}]}
        recipe_saved = await cook.put(path + "/recipe", json=recipe)
        check(recipe_saved.status_code == 200, recipe_saved.text)
        check((await cook.put(path + "/recipe", json=recipe)).status_code == 409, "Stale recipe must conflict")
        check((await cook.put(path + "/recipe", json={**recipe, "expected_version": 1, "status": "APPROVED"})).status_code == 403,
              "COOK must not approve recipe")
        stored = await conn.fetchrow('SELECT "nameRu",recipe FROM kitchen_menu_items WHERE id=$1::uuid', draft_id)
        check(stored["nameRu"] == "Исправленный черновик" and stored["recipe"] is not None,
              "Draft name/recipe not stored in PostgreSQL")
        owner_menu = await owner.get("/api/v1/kitchen/menu")
        check(any(row["id"] == draft_id for row in owner_menu.json()["items"]), "Management cannot see draft")
        approved_recipe = await owner.put(path + "/recipe", json={**recipe, "expected_version": 1, "status": "APPROVED"})
        check(approved_recipe.status_code == 200, approved_recipe.text)
        check((await owner.patch(path, json={"is_active": True, "is_draft": False, "price_kgs": 222})).status_code == 200,
              "Owner publication failed")
        check((await cook.patch(path, json={"name_ru": "Forbidden"})).status_code == 403,
              "COOK must not edit published dish")
        check((await cook.put(path + "/recipe", json={**recipe, "expected_version": 2})).status_code == 403,
              "COOK must not change published recipe")

        audit_count = await conn.fetchval(
            '''SELECT count(*) FROM audit_logs WHERE resource='KitchenMenuItem' AND "resourceId"=$1
               AND action IN ('CREATE_MENU_ITEM','UPDATE_MENU_ITEM') AND result='SUCCESS' ''',
            item["id"],
        )
        check(audit_count >= 2, f"expected menu audit entries, got {audit_count}")
        print("KITCHEN MENU MANAGEMENT E2E: PASS")
    finally:
        await owner.aclose()
        await cook.aclose()
        await conn.execute('DELETE FROM kitchen_menu_items WHERE code=ANY($1::text[])', [code, code + '_COOK'])
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
