"""Exercise recipe storage, optimistic writes and exact requirements on a test DB."""
import asyncio
import os
import uuid
from decimal import Decimal

import asyncpg
import httpx


async def main():
    if os.environ.get("ALLOW_KITCHEN_RECIPE_TEST_WRITES") != "1":
        raise RuntimeError("Explicit test-write opt-in required")
    db = await asyncpg.connect(os.environ["DATABASE_URL"].split("?", 1)[0])
    owner = httpx.AsyncClient(base_url=os.environ.get("CORE_API_URL", "http://127.0.0.1:8000"), timeout=20)
    cook = httpx.AsyncClient(base_url=os.environ.get("CORE_API_URL", "http://127.0.0.1:8000"), timeout=20)
    item_id = None
    code = "RECIPE_QA_" + uuid.uuid4().hex[:10].upper()
    try:
        for client, username, password in (
            (owner, os.environ["BOOTSTRAP_OWNER_USERNAME"], os.environ["BOOTSTRAP_OWNER_PASSWORD"]),
            (cook, os.environ.get("KITCHEN_MENU_COOK_USERNAME") or os.environ["KITCHEN_MENU_DINING_USERNAME"],
             os.environ.get("KITCHEN_MENU_COOK_PASSWORD") or os.environ["KITCHEN_MENU_DINING_PASSWORD"]),
        ):
            result = await client.post("/api/v1/auth/login", json={"username":username,"password":password})
            assert result.status_code == 200, result.status_code
            client.headers["Cookie"] = "; ".join(f"{key}={value}" for key,value in result.cookies.items())
        identity = (await owner.get("/api/v1/auth/me")).json()
        pid = await db.fetchval("SELECT id FROM properties WHERE code=$1", identity["property_code"])
        today = await db.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1", pid)
        before_payments = await db.fetchval("SELECT count(*) FROM payments")
        created = await owner.post("/api/v1/kitchen/menu",json={
            "code":code,"category":"MAIN","name_ru":code,"name_kg":code,"name_en":code,
            "name_kz":code,"price_kgs":0,"is_active":True,"is_draft":False,
        })
        assert created.status_code == 201, created.text
        item_id = created.json()["id"]
        path = "/api/v1/kitchen/menu/" + item_id + "/recipe"
        draft = {"expected_version":0,"status":"DRAFT","is_sample":True,
                 "ingredients":[{"name":code+" rice","unit":"KG","quantity_per_portion":"0.1"}]}
        assert (await cook.put(path,json=draft)).status_code == 403
        assert (await owner.get("/api/v1/kitchen/menu/"+str(uuid.uuid4())+"/recipe")).status_code == 404
        saved = await owner.put(path,json=draft)
        assert saved.status_code == 200, saved.text
        assert saved.json()["recipe"]["version"] == 1
        plan = {"menu_item_id":item_id,"service_date":today.isoformat(),"meal_type":"LUNCH",
                "planned_quantity":20,"prepared_quantity":8}
        result = await cook.put("/api/v1/kitchen/production-targets",json=plan)
        assert result.status_code == 200,result.text
        params={"from_date":today.isoformat(),"through_date":today.isoformat()}
        result = (await owner.get("/api/v1/kitchen/production-targets",params=params)).json()
        assert any(row["menu_item_id"]==item_id for row in result["ingredient_requirements"]["missing_recipes"])
        approved={**draft,"expected_version":1,"status":"APPROVED"}
        saved=await owner.put(path,json=approved)
        assert saved.status_code==200,saved.text
        assert (await owner.put(path,json=approved)).status_code==409
        updates=[]
        for norm in ("0.2","0.3"):
            updates.append({**approved,"expected_version":2,"ingredients":[
                {"name":code+" rice","unit":"KG","quantity_per_portion":norm}]})
        concurrent=await asyncio.gather(*(owner.put(path,json=value) for value in updates))
        assert sorted(r.status_code for r in concurrent)==[200,409]
        actual=(await cook.get(path)).json()["recipe"]
        assert actual["version"]==3
        norm=Decimal(actual["ingredients"][0]["quantity_per_portion"])
        result=await owner.get("/api/v1/kitchen/production-targets",params=params)
        assert result.status_code==200,result.text
        owner_body=result.json()
        cook_body=(await cook.get("/api/v1/kitchen/production-targets",params=params)).json()
        assert owner_body==cook_body
        product=next(x for x in owner_body["ingredient_requirements"]["items"] if x["name"]==code+" rice")
        assert Decimal(product["planned_quantity"])==20*norm
        assert Decimal(product["prepared_quantity"])==8*norm
        assert Decimal(product["remaining_quantity"])==12*norm
        assert owner_body["ingredient_requirements"]["contains_sample_data"] is True
        stored=await db.fetchval('SELECT recipe FROM kitchen_menu_items WHERE id=$1::uuid',item_id)
        assert stored is not None
        assert await db.fetchval("SELECT count(*) FROM payments")==before_payments
        print("PASS recipes: persisted versions, COOK read-only, conflict retry, concurrent updates, exact totals, OWNER=COOK, no payments")
    finally:
        if item_id:
            await db.execute('DELETE FROM kitchen_menu_items WHERE id=$1::uuid AND "propertyId"=$2',item_id,pid)
        await owner.aclose()
        await cook.aclose()
        await db.close()


if __name__=="__main__":
    asyncio.run(main())
