"""Isolated real PostgreSQL stock loss E2E: roles, balance, audit and replay."""
import asyncio
import os
import uuid
from decimal import Decimal

import asyncpg
import httpx
from kitchen_e2e_target_guard import validate_target

BASE=os.environ.get("CORE_API_URL","http://127.0.0.1:8000")
DB=os.environ["DATABASE_URL"].split("?",1)[0]
PROPERTY=os.environ.get("PROPERTY_CODE","THREE_CROWNS")
validate_target(
    base=BASE,database_url=DB,property_code=PROPERTY,
    cookie_secure=os.environ.get("COOKIE_SECURE","false").lower() in {"1","true","yes"},
    rc426_confirm=os.environ.get("RC426_KITCHEN_E2E_CONFIRM"),
)


def require(response,code,label):
    assert response.status_code==code, f"{label}: {response.status_code} {response.text}"
    return response.json()


async def login(client,username,password,role):
    require(await client.post("/api/v1/auth/login",json={
        "username":username,"password":password}),200,role+" login")
    me=require(await client.get("/api/v1/auth/me"),200,role+" me")
    assert me["role"]==role and me["property_code"]==PROPERTY
    return me


async def main():
    db=await asyncpg.connect(DB)
    try:
        pid=await db.fetchval('SELECT id FROM properties WHERE code=$1',PROPERTY)
        assert pid is not None
        payments_before=await db.fetchval('SELECT count(*) FROM payments')
        async with httpx.AsyncClient(base_url=BASE,timeout=35) as owner, \
                   httpx.AsyncClient(base_url=BASE,timeout=35) as cook, \
                   httpx.AsyncClient(base_url=BASE,timeout=35) as waiter:
            await login(owner,os.environ["BOOTSTRAP_OWNER_USERNAME"],
                        os.environ["BOOTSTRAP_OWNER_PASSWORD"],"OWNER")
            cook_me=await login(cook,os.environ["KITCHEN_MENU_DINING_USERNAME"],
                                os.environ["KITCHEN_MENU_DINING_PASSWORD"],"COOK")
            await login(waiter,os.environ["WAITER_SERVE_E2E_USERNAME"],
                        os.environ["WAITER_SERVE_E2E_PASSWORD"],"WAITER")
            created=require(await owner.post("/api/v1/kitchen/stock/items",json={
                "name":"Loss E2E "+uuid.uuid4().hex[:12],
                "unit":"KG","cost_per_unit_kgs":"140.50","is_sample":False,
            }),201,"stock item")
            iid=created["id"]
            # The database must reject null loss reasons even if someone bypasses the API.
            try:
                async with db.transaction():
                    await db.execute(
                        '''INSERT INTO kitchen_stock_movements
                           (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","createdById",notes)
                           VALUES ($1,$2,$3,'WASTE',$4,$5,$6,NULL)''',
                        uuid.uuid4(),pid,uuid.UUID(iid),Decimal("0.01"),
                        Decimal("140.50"),uuid.UUID(cook_me["id"]),
                    )
            except asyncpg.CheckViolationError:
                pass
            else:
                raise AssertionError("PostgreSQL must reject null WASTE reason")
            require(await owner.post("/api/v1/kitchen/stock/receipts",json={
                "stock_item_id":iid,"quantity":"10","notes":"Isolated stock loss test",
            }),201,"stock receipt")
            before=require(await owner.get("/api/v1/kitchen/stock"),200,"before snapshot")
            row=next(x for x in before["items"] if x["id"]==iid)
            assert Decimal(row["balance"])==10
            base_cost=Decimal(before["production_cost_kgs"])
            assert require(await waiter.get("/api/v1/kitchen/stock/losses"),403,
                           "WAITER denied loss history") is not None
            mid=str(uuid.uuid4())
            payload={"movement_id":mid,"stock_item_id":iid,"kind":"SPOILAGE",
                     "quantity":"2.25","reason":"  Expired   batch "}
            require(await waiter.post("/api/v1/kitchen/stock/losses",json=payload),
                    403,"WAITER cannot debit stock")
            created_loss=require(await cook.post("/api/v1/kitchen/stock/losses",json=payload),
                                 201,"COOK spoilage")
            assert created_loss["id"]==mid and created_loss["already_processed"] is False
            assert Decimal(created_loss["cost_kgs"])==Decimal("316.125")
            assert created_loss["payment_created"] is False
            again=require(await cook.post("/api/v1/kitchen/stock/losses",json=payload),
                          201,"idempotent replay")
            assert again["id"]==mid and again["already_processed"] is True
            require(await cook.post("/api/v1/kitchen/stock/losses",json={
                **payload,"quantity":"1.5",
            }),409,"reject changed idempotency payload")
            require(await cook.post("/api/v1/kitchen/stock/losses",json={
                **payload,"movement_id":str(uuid.uuid4()),"quantity":"8",
            }),409,"reject overdraw")
            require(await cook.post("/api/v1/kitchen/stock/losses",json={
                **payload,"movement_id":str(uuid.uuid4()),"quantity":"0",
            }),422,"reject zero quantity")
            require(await cook.post("/api/v1/kitchen/stock/losses",json={
                **payload,"movement_id":str(uuid.uuid4()),"reason":"x",
            }),422,"reject missing reason")
            loss_id=str(uuid.uuid4())
            waste=require(await owner.post("/api/v1/kitchen/stock/losses",json={
                "movement_id":loss_id,"stock_item_id":iid,"kind":"WASTE",
                "quantity":"1.75","reason":"Unusable service leftovers",
            }),201,"OWNER waste")
            assert Decimal(waste["cost_kgs"])==Decimal("245.875")
            stock=require(await owner.get("/api/v1/kitchen/stock"),200,"after snapshot")
            row=next(x for x in stock["items"] if x["id"]==iid)
            assert Decimal(row["balance"])==6
            assert Decimal(stock["production_cost_kgs"])==base_cost, "loss must not inflate production cost"
            history=require(await cook.get("/api/v1/kitchen/stock/losses"),200,"loss ledger")
            assert history["financial_truth"]=="INVENTORY_LOSS_NOT_PAYMENT"
            records=[x for x in history["items"] if x["id"] in {mid,loss_id}]
            assert len(records)==2 and {x["kind"] for x in records}=={"SPOILAGE","WASTE"}
            assert next(x for x in records if x["id"]==mid)["created_by_id"]==cook_me["id"]
            stored=await db.fetch(
                '''SELECT id,kind,quantity,notes,"createdById","unitCostKgs","propertyId",
                          "productionTargetId"
                   FROM kitchen_stock_movements WHERE id=ANY($1::uuid[])''',
                [uuid.UUID(mid),uuid.UUID(loss_id)])
            assert len(stored)==2
            assert all(x["propertyId"]==pid and x["productionTargetId"] is None for x in stored)
            assert next(x for x in stored if str(x["id"])==mid)["notes"]=="Expired batch"
            assert await db.fetchval('SELECT count(*) FROM payments')==payments_before
            print("KITCHEN STOCK WASTE/SPOILAGE POSTGRES E2E: PASS")
    finally:
        await db.close()


if __name__=="__main__":
    asyncio.run(main())
