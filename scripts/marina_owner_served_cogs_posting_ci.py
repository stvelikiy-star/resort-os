"""Isolated two-hotel COGS posting acceptance; requires served batch CI first.

A complete operator-attested allocation with matching folio is required.
All amounts and classifications come from PostgreSQL, never test input.
"""
import asyncio
import os
import uuid
from urllib.parse import urlsplit
import asyncpg
from fastapi.testclient import TestClient
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

url=urlsplit(os.getenv("DATABASE_URL","").split("?",1)[0])
assert url.hostname in ("localhost","127.0.0.1") and url.path=="/marina_shared_browser_ci"
assert os.getenv("APP_ENV")=="staging"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM")=="DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED")=="true"
assert os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED")=="true"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED")=="false"
assert os.getenv("PROPERTY_CODE")=="HOTEL_A"

checks=0
def check(actual,expected,label):
    global checks
    assert actual==expected,(label,actual,expected)
    checks+=1

async def source():
    conn=await asyncpg.connect(url.geturl())
    try:
        a=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_A'")
        b=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_B'")
        row=await conn.fetchrow(
            """SELECT o.id,(o."completedAt" AT TIME ZONE p.timezone)::date AS day,
                      COALESCE(SUM(l."totalCostKgs"),0) AS cost
               FROM kitchen_orders o
               JOIN properties p ON p.id=o."propertyId"
               JOIN kitchen_served_batch_allocations l
                 ON l."orderId"=o.id AND l."propertyId"=o."propertyId"
               WHERE o."propertyId"=$1 AND o.status='SERVED'
               GROUP BY o.id,o."completedAt",p.timezone
               HAVING COALESCE(SUM(l."totalCostKgs"),0)=84
               ORDER BY o.id LIMIT 1""",a)
        assert a and b and row and row["day"]
        assert await conn.fetchval(
           "SELECT owner_accounting_served_cogs_proof($1,$2,$3)",
           a,row["id"],row["day"]) is None
        return a,b,row["id"],row["day"],row["cost"]
    finally:
        await conn.close()

pid,other_pid,order_id,service_date,cost=asyncio.run(source())
base="/api/v1/admin/finance/owner/accounting-journal"
with TestClient(app,base_url="https://marina-cogs-ci.invalid") as client:
    def login(name):
        client.post("/api/v1/auth/logout")
        r=client.post("/api/v1/auth/login",json={"username":name,"password":PASSWORD})
        check(r.status_code,200,"owner login "+name)

    login("owner")
    proposal=uuid.uuid4()
    payload={"id":str(proposal),"source_type":"STOCK_CONSUMPTION",
       "source_id":str(order_id),"accounting_date":service_date.isoformat(),
       "policy_version":"CI-SERVED-COGS-1",
       "reason":"Actual served batch and source folio cost reconciliation",
       "lines":[
         {"account_code":"5100","side":"DEBIT","amount_kgs":"84.0000"},
         {"account_code":"1300","side":"CREDIT","amount_kgs":"84.0000"}]}
    before=client.post(base+"/proposals",json=payload)
    check(before.status_code,409,"served order without folio rejected")

async def attach_folio():
    conn=await asyncpg.connect(url.geturl())
    try:
        reservation=uuid.uuid4()
        folio=uuid.uuid4()
        await conn.execute(
            """INSERT INTO reservations
               (id,"propertyId","bookingNumber","checkIn","checkOut",adults,
                children,"totalKgs","updatedAt")
               VALUES($1,$2,$3,$4,$5,1,0,700,now())""",
            reservation,pid,"COGS-CI-"+str(uuid.uuid4())[:12],service_date,
            service_date+__import__("datetime").timedelta(days=1))
        await conn.execute(
            """INSERT INTO guest_folio_charges
               (id,"propertyId","reservationId","sourceType","sourceId",
                code,description,"amountKgs",status,"serviceDate","createdByType")
               VALUES($1,$2,$3,'KITCHEN_ORDER',$4,
                      'DINING','Synthetic served source matched to folio',
                      700,'OPEN',$5,'STAFF')""",
            folio,pid,reservation,order_id,service_date)
        await conn.execute(
            """UPDATE kitchen_orders
               SET "reservationId"=$1,"folioChargeId"=$2,"updatedAt"=now()
               WHERE id=$3 AND "propertyId"=$4""",
            reservation,folio,order_id,pid)
        actual=await conn.fetchval(
            "SELECT owner_accounting_served_cogs_proof($1,$2,$3)",
            pid,order_id,service_date)
        check(actual,cost,"fully linked source costs exact same amount")
    finally:
        await conn.close()

asyncio.run(attach_folio())
with TestClient(app,base_url="https://marina-cogs-ci.invalid") as client:
    def login(name):
        client.post("/api/v1/auth/logout")
        r=client.post("/api/v1/auth/login",json={"username":name,"password":PASSWORD})
        check(r.status_code,200,"owner login "+name)

    login("owner")
    created=client.post(base+"/proposals",json=payload)
    check(created.status_code,201,"verified COGS proposal")
    path=base+"/proposals/"+str(proposal)
    login("accounting_reviewer")
    approval=client.post(path+"/decisions",json={
      "id":str(uuid.uuid4()),"action":"APPROVE",
      "reason":"Independently reviewed full batch served portions"})
    check(approval.status_code,201,"independent COGS approval")
    posted_id=uuid.uuid4()
    post={"id":str(posted_id),
          "reason":"Exactly matched source batches and folio posting"}
    posted=client.post(path+"/post",json=post)
    check(posted.status_code,201,"posted served COGS")
    check(posted.json()["accounting_posted"],True,"posting actually persisted")
    check(posted.json()["recognized_profit_kgs"],None,"period profit still null")
    check(client.post(path+"/post",json=post).json()["already_processed"],
          True,"idempotent COGS posting")
    rev=client.post(path+"/decisions",json={
       "id":str(uuid.uuid4()),"action":"REVERSE",
       "reason":"Independent correction of served-cost evidence"})
    check(rev.status_code,201,"COGS reversal decision")
    reverse={"id":str(uuid.uuid4()),
             "reason":"Reversal of original served COGS journal entry"}
    reversed_post=client.post(base+"/postings/"+str(posted_id)+"/reverse",
                              json=reverse)
    check(reversed_post.status_code,201,"exact COGS reversal")
    check(client.post(base+"/postings/"+str(posted_id)+"/reverse",
                      json=reverse).json()["already_processed"],
          True,"reversal idempotency")
    statement=client.get(base+"/posted-profit",params={
      "from_date":service_date.isoformat(),"to_date":service_date.isoformat()})
    check(statement.status_code,200,"COGS statement")
    check(statement.json()["recognized_profit_kgs"],None,
          "profit not recognized before complete period close")

async def verify():
    conn=await asyncpg.connect(url.geturl())
    try:
        count=await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_postings
               WHERE "propertyId"=$1 AND "proposalId"=$2""",pid,proposal)
        check(count,2,"exact original plus reverse entries")
        balance=await conn.fetchval(
            """SELECT COALESCE(SUM(CASE WHEN l.side='DEBIT' THEN l."amountKgs"
                    ELSE -l."amountKgs" END),0)
               FROM owner_accounting_posting_lines l
               JOIN owner_accounting_postings p
                 ON p.id=l."postingId" AND p."propertyId"=l."propertyId"
               WHERE p."propertyId"=$1 AND p."proposalId"=$2
                 AND l."accountCode"='5100'""",pid,proposal)
        check(balance,0,"COGS reversed exactly to zero")
        foreign=await conn.fetchval(
            'SELECT count(*) FROM owner_accounting_postings WHERE "propertyId"=$1',
            other_pid)
        check(foreign,0,"HOTEL_B has no foreign accounting postings")
    finally:
        await conn.close()

asyncio.run(verify())
print("MARINA_OWNER_SERVED_COGS_TWO_HOTEL_POST_REVERSE_PASS",checks)
