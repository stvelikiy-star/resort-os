"""Real PostgreSQL E2E for kitchen procurement: recipe need -> request -> approve -> receive.

Never points at production, never calls payment providers. CI disposable hotel only.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import asyncpg
import httpx


def verify(response, expected, what):
    assert response.status_code==expected, f"{what}: {response.status_code} {response.text}"
    return response.json()


async def authenticate(client, username, password, role):
    response=await client.post("/api/v1/auth/login",json={"username":username,"password":password})
    verify(response,200,role+" login")
    client.headers["Cookie"]="; ".join(f"{k}={v}" for k,v in response.cookies.items())
    me=verify(await client.get("/api/v1/auth/me"),200,role+" me")
    assert me["role"]==role
    return me


async def main():
    if os.environ.get("ALLOW_KITCHEN_PROCUREMENT_TEST_WRITES")!="1":
        raise RuntimeError("Explicit isolated PostgreSQL test-write opt-in required")
    url=os.environ["DATABASE_URL"].split("?",1)[0]
    if not ("localhost" in url or "127.0.0.1" in url):
        raise RuntimeError("Refusing non-local PostgreSQL test target")
    base=os.environ.get("CORE_API_URL","http://127.0.0.1:8000")
    if not base.startswith("http://127.0.0.1:"):
        raise RuntimeError("Refusing remote API")
    db=await asyncpg.connect(url)
    code="PROC_E2E_"+uuid.uuid4().hex[:10].upper()
    menu_id=None
    pid=None
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner, \
                   httpx.AsyncClient(base_url=base,timeout=30) as cook, \
                   httpx.AsyncClient(base_url=base,timeout=30) as store, \
                   httpx.AsyncClient(base_url=base,timeout=30) as waiter:
            owner_me=await authenticate(owner,os.environ["BOOTSTRAP_OWNER_USERNAME"],
                                        os.environ["BOOTSTRAP_OWNER_PASSWORD"],"OWNER")
            await authenticate(cook,os.environ["KITCHEN_MENU_DINING_USERNAME"],
                               os.environ["KITCHEN_MENU_DINING_PASSWORD"],"COOK")
            store_me=await authenticate(store,os.environ["PROC_STORE_USERNAME"],
                                        os.environ["PROC_STORE_PASSWORD"],"STORE_STAFF")
            await authenticate(waiter,os.environ["WAITER_SERVE_E2E_USERNAME"],
                               os.environ["WAITER_SERVE_E2E_PASSWORD"],"WAITER")
            pid=await db.fetchval("SELECT id FROM properties WHERE code=$1",owner_me["property_code"])
            assert pid is not None
            today=await db.fetchval(
                "SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1",pid)
            payment_count=await db.fetchval("SELECT count(*) FROM payments")
            menu_id=verify(await owner.post("/api/v1/kitchen/menu",json={
                "code":code,"category":"MAIN","name_ru":code,"name_kg":code,
                "name_en":code,"name_kz":code,"price_kgs":0,"is_active":True,"is_draft":False,
            }),201,"menu create")["id"]
            verify(await owner.put("/api/v1/kitchen/menu/"+menu_id+"/recipe",json={
                "expected_version":0,"status":"APPROVED","is_sample":False,
                "ingredients":[{"name":code+" ingredient","unit":"KG",
                                "quantity_per_portion":"0.5"}],
            }),200,"approved recipe")
            verify(await cook.put("/api/v1/kitchen/production-targets",json={
                "menu_item_id":menu_id,"service_date":today.isoformat(),"meal_type":"LUNCH",
                "planned_quantity":20,"prepared_quantity":8,
            }),200,"dated production")
            item_id=verify(await owner.post("/api/v1/kitchen/stock/items",json={
                "name":code+" ingredient","unit":"KG",
                "cost_per_unit_kgs":"100","is_sample":False,
            }),201,"stock item")["id"]
            verify(await owner.post("/api/v1/kitchen/stock/receipts",json={
                "stock_item_id":item_id,"quantity":"1","notes":"CI initial stock",
            }),201,"initial receipt")
            needs=verify(await cook.get("/api/v1/kitchen/procurement/needs",
                    params={"service_date":today.isoformat()}),200,"production needs")
            line=next(r for r in needs["items"] if r["stock_item_id"]==item_id)
            assert Decimal(line["remaining_needed"])==Decimal("6"),line
            assert Decimal(line["balance"])==Decimal("1"),line
            assert Decimal(line["shortage"])==Decimal("5"),line
            assert needs["inventory_deducted"] is False and needs["payment_created"] is False
            verify(await waiter.get("/api/v1/kitchen/procurement/requests"),403,"waiter read denied")
            req_id=str(uuid.uuid4())
            payload={"request_id":req_id,"stock_item_id":item_id,"quantity":"5",
                     "service_date":today.isoformat(),"notes":"  Production   demand "}
            verify(await waiter.post("/api/v1/kitchen/procurement/requests",json=payload),
                   403,"waiter request denied")
            created=verify(await cook.post("/api/v1/kitchen/procurement/requests",json=payload),
                           201,"cook request")
            assert created["status"]=="REQUESTED"
            replay=verify(await cook.post("/api/v1/kitchen/procurement/requests",json=payload),
                          201,"request replay")
            assert replay["status"]=="EXISTS"
            verify(await cook.post("/api/v1/kitchen/procurement/requests",json={
                **payload,"quantity":"4",
            }),409,"conflicting request id")
            verify(await cook.post(f"/api/v1/kitchen/procurement/requests/{req_id}/approve"),
                   403,"cook cannot approve")
            verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/approve"),
                   403,"store cannot approve")
            first_id=str(uuid.uuid4())
            verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                    json={"receipt_id":first_id,"quantity":"2"}),
                   409,"cannot receive before approval")
            needs=verify(await owner.get("/api/v1/kitchen/procurement/needs",
                                       params={"service_date":today.isoformat()}),200,"pipeline")
            line=next(r for r in needs["items"] if r["stock_item_id"]==item_id)
            assert Decimal(line["pending_requests"])==Decimal("5")
            assert Decimal(line["shortage_after_pipeline"])==Decimal("0")
            approved=verify(await owner.post(f"/api/v1/kitchen/procurement/requests/{req_id}/approve"),
                            200,"owner approval")
            assert approved["status"]=="APPROVED" and approved["payment_created"] is False
            again=verify(await owner.post(f"/api/v1/kitchen/procurement/requests/{req_id}/approve"),
                         200,"approval replay")
            assert again["already_processed"] is True
            partial=verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                             json={"receipt_id":first_id,"quantity":"2"}),
                           201,"partial receive")
            assert partial["status"]=="PARTIAL" and partial["already_processed"] is False
            duplicate=verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                              json={"receipt_id":first_id,"quantity":"2"}),
                             201,"receipt idempotency")
            assert duplicate["already_processed"] is True
            verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                    json={"receipt_id":first_id,"quantity":"3"}),
                   409,"conflicting receipt replay")
            verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                    json={"receipt_id":str(uuid.uuid4()),"quantity":"4"}),
                   409,"over-receipt blocked")
            second_id=str(uuid.uuid4())
            result=verify(await store.post(f"/api/v1/kitchen/procurement/requests/{req_id}/receive",
                                            json={"receipt_id":second_id,"quantity":"3"}),
                          201,"complete receipt")
            assert result["status"]=="RECEIVED" and result["payment_created"] is False
            ledger=verify(await cook.get("/api/v1/kitchen/procurement/requests"),200,"read ledger")
            request_row=next(r for r in ledger["items"] if r["id"]==req_id)
            assert request_row["status"]=="RECEIVED" and Decimal(request_row["received_quantity"])==5
            stock=verify(await store.get("/api/v1/kitchen/stock"),200,"stock balance after receipt")
            item=next(r for r in stock["items"] if r["id"]==item_id)
            assert Decimal(item["balance"])==6, item
            assert await db.fetchval("SELECT count(*) FROM payments")==payment_count
            receipts=await db.fetch(
                '''SELECT m.id,m.kind,m.quantity,m."createdById",p."requestId"
                   FROM kitchen_stock_movements m JOIN kitchen_procurement_receipts p ON p.id=m.id
                   WHERE m.id=ANY($1::uuid[])''',
                [uuid.UUID(first_id),uuid.UUID(second_id)])
            assert len(receipts)==2 and all(r["kind"]=="RECEIPT" for r in receipts)
            assert all(str(r["createdById"])==store_me["id"] for r in receipts)
            print("KITCHEN PROCUREMENT REAL POSTGRES E2E PASS: needs -> COOK request -> OWNER approval -> STORE partial+final receipt, role denial, idempotency, inventory, no payment")
    finally:
        # CI database is disposable; keep the procurement chain for post-test inspection.
        await db.close()


if __name__=="__main__":
    asyncio.run(main())
