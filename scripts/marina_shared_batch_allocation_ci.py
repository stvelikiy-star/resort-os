"""Real PostgreSQL TWO-hotel operator-attested batch -> served order item CI.

Scope: test-only synthetic CI DB with strict localhost name and staging flags.
Validates cross-hotel denial, menu/capacity constraints, exact cost, replay
idempotency, audit trail and absence of payment/accounting postings.
"""
import asyncio
import os
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4

import asyncpg
from fastapi.testclient import TestClient

from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

url = urlparse(os.getenv("DATABASE_URL","").split("?",1)[0])
assert os.getenv("MARINA_BATCH_ALLOCATION_CI_CONFIRM")=="ISOLATED_BATCH_ALLOCATION_ONLY"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM")=="DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED")=="true"
assert os.getenv("APP_ENV")=="staging"
assert url.hostname in ("localhost","127.0.0.1") and url.path=="/marina_shared_browser_ci"
assert os.getenv("MARINA_SHARED_BROWSER_CI_PASSWORD","").startswith("synthetic-ci-only-")

async def seed():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].split("?")[0])
    try:
        facts = {}
        async with conn.transaction():
            assert await conn.fetchval("SELECT count(*) FROM properties")==2
            for hotel in ("A","B"):
                pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", "HOTEL_"+hotel)
                owner = await conn.fetchval(
                    """SELECT id FROM staff_users WHERE "propertyId"=$1 AND role='OWNER'""",pid)
                assert pid and owner
                menu,target,stock,order,item = (uuid4() for _ in range(5))
                today = await conn.fetchval("SELECT (now() AT TIME ZONE 'Asia/Bishkek')::date")
                await conn.execute(
                    """INSERT INTO kitchen_menu_items
                       (id,"propertyId",code,category,"nameRu","nameKg","nameEn",
                       "priceKgs","isActive","isDraft")
                       VALUES($1,$2,$3,'MAIN','Batch CI','Batch CI','Batch CI',100,true,false)""",
                    menu,pid,"BATCH_CI_"+hotel)
                await conn.execute(
                    """INSERT INTO kitchen_production_targets
                       (id,"propertyId","menuItemId","serviceDate","mealType",
                       "plannedQuantity","preparedQuantity")
                       VALUES($1,$2,$3,$4,'LUNCH',10,10)""",
                    target,pid,menu,today)
                await conn.execute(
                    """INSERT INTO kitchen_stock_items
                       (id,"propertyId",name,"nameKey",unit,"costPerUnitKgs","isSample")
                       VALUES($1,$2,$3,$4,'KG',12,false)""",
                    stock,pid,"Batch ingredient "+hotel,"batch ingredient "+hotel.lower())
                await conn.execute(
                    """INSERT INTO kitchen_stock_movements
                       (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","createdById")
                       VALUES($1,$2,$3,'RECEIPT',10,12,$4)""",uuid4(),pid,stock,owner)
                await conn.execute(
                    """INSERT INTO kitchen_stock_movements
                       (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs",
                        "productionTargetId","preparedFrom","preparedTo","createdById")
                       VALUES($1,$2,$3,'PRODUCTION',10,12,$4,0,10,$5)""",
                    uuid4(),pid,stock,target,owner)
                await conn.execute(
                    """INSERT INTO kitchen_stock_production_progress
                       ("propertyId","productionTargetId","deductedPortions")
                       VALUES($1,$2,10)""",pid,target)
                await conn.execute(
                    """INSERT INTO kitchen_orders
                       (id,"propertyId","orderNumber",status,source,"guestCount",
                        "mealType","totalKgs","openedById","completedAt")
                       VALUES($1,$2,$3,'SERVED','TABLE',2,'LUNCH',700,$4,now())""",
                    order,pid,"BATCH-CI-"+hotel,owner)
                await conn.execute(
                    """INSERT INTO kitchen_order_items
                       (id,"orderId","menuItemId",quantity,"unitPriceKgs",
                        "lineTotalKgs",status)
                       VALUES($1,$2,$3,7,100,700,'SERVED')""",item,order,menu)
                facts[hotel]={"property":pid,"order":order,"item":item,"target":target}
        return facts
    finally:
        await conn.close()

facts = asyncio.run(seed())

async def payment_count():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"].split("?")[0])
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM payments")
    finally:
        await conn.close()

# Earlier lifecycle steps may legitimately seed payments in the shared disposable DB.
# The batch-allocation operation must not create additional payment records.
payments_before = asyncio.run(payment_count())
checks=0
with TestClient(app,base_url="https://batch-isolated.invalid") as client:
    def login(code,role):
        r=client.post("/api/v1/auth/login",json={
            "username":role.lower(),"password":PASSWORD,
            "tenant_code":"tenant_"+code.lower(),"property_code":"HOTEL_"+code})
        assert r.status_code==200,r.text

    for hotel in ("A","B"):
        other="B" if hotel=="A" else "A"
        own=facts[hotel];far=facts[other]
        path=f'/api/v1/kitchen/orders/{own["order"]}/batch-allocations'
        good={"id":str(uuid4()),"order_item_id":str(own["item"]),
              "production_target_id":str(own["target"]),"portions":7}
        login(hotel,"WAITER")
        assert client.get(path).status_code==403
        checks+=1
        assert client.post(path,json=good).status_code==403
        checks+=1
        client.post("/api/v1/auth/logout")
        login(hotel,"COOK")
        targets=client.get("/api/v1/kitchen/production-targets")
        assert targets.status_code==200,targets.text
        assert any(str(t["id"])==str(own["target"]) for t in targets.json()["items"])
        checks+=2
        foreign_read=client.get(f'/api/v1/kitchen/orders/{far["order"]}/batch-allocations')
        assert foreign_read.status_code==404,foreign_read.text
        checks+=1
        foreign=client.post(
            f'/api/v1/kitchen/orders/{far["order"]}/batch-allocations',
            json={"id":str(uuid4()),"order_item_id":str(far["item"]),
                  "production_target_id":str(far["target"]),"portions":1})
        assert foreign.status_code==404,foreign.text
        checks+=1
        wrong=client.post(path,json={**good,"id":str(uuid4()),
                 "production_target_id":str(far["target"])})
        assert wrong.status_code==404,wrong.text
        checks+=1
        created=client.post(path,json=good)
        assert created.status_code==201,created.text
        assert created.json()["cost_kgs"]=="84.0000",created.text
        assert created.json()["recognized_profit_posted"] is False
        readback=client.get(path)
        assert readback.status_code==200,readback.text
        assert len(readback.json()["items"])==1,readback.text
        assert readback.json()["items"][0]["portions"]==7
        assert Decimal(readback.json()["items"][0]["cost_kgs"])==Decimal(84)
        checks+=7
        repeated=client.post(path,json=good)
        assert repeated.status_code==201 and repeated.json()["already_processed"] is True
        checks+=1
        too_much=client.post(path,json={**good,"id":str(uuid4()),"portions":1})
        assert too_much.status_code==409,too_much.text
        assert too_much.json()["detail"]["code"]=="BATCH_ITEM_PAIR_ALREADY_ALLOCATED"
        checks+=2
        reused=client.post(path,json={**good,"portions":3})
        assert reused.status_code==409
        checks+=1
        client.post("/api/v1/auth/logout")
        login(hotel,"OWNER")
        period=client.get("/api/v1/admin/finance/owner/accrual-readiness",params={
            "from_date": date.today().isoformat(), "to_date":date.today().isoformat()})
        assert period.status_code==200,period.text
        evidence=period.json()["served_kitchen_cost_trace"]["operator_attested_batch_links"]
        assert evidence["attributed_portions"]==7,evidence
        assert evidence["served_portions"]==evidence["attributed_portions"]+evidence["unattributed_served_portions"],evidence
        assert Decimal(evidence["attributed_cost_kgs"])==Decimal(84),evidence
        assert len(evidence["allocations"])==1,evidence
        assert evidence["cost_is_recognized_cogs"] is False
        assert period.json()["recognition"]["recognized_profit_kgs"] is None
        checks+=5
        client.post("/api/v1/auth/logout")

async def verify():
    conn=await asyncpg.connect(os.environ["DATABASE_URL"].split("?")[0])
    try:
        for hotel in ("A","B"):
            p=facts[hotel]["property"]
            row=await conn.fetchrow(
                """SELECT COUNT(*)::int AS cnt, COALESCE(SUM(portions),0)::int AS portions,
                          COALESCE(SUM("totalCostKgs"),0) AS cost
                   FROM kitchen_served_batch_allocations WHERE "propertyId"=$1""",p)
            assert row["cnt"]==1 and row["portions"]==7
            assert Decimal(row["cost"])==Decimal(84)
            proof=await conn.fetchval(
                """SELECT COUNT(*)::int FROM audit_logs
                   WHERE "propertyId"=$1 AND action='KITCHEN_SERVED_BATCH_ALLOCATION'""",p)
            assert proof==1
        assert await conn.fetchval("SELECT COUNT(*) FROM payments")==payments_before
    finally:
        await conn.close()
asyncio.run(verify())
print("MARINA_TWO_HOTEL_EXACT_BATCH_LINK_PASS",checks+7)
