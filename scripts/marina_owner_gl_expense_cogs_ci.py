"""Staged OWNER GL receipt/expense/COGS e2e on disposable two-hotel PostgreSQL.

Runs after the two-hotel source, batch and independent reviewer CI fixtures.
No production modifications or user passwords.
"""
import asyncio
import os
from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
from fastapi.testclient import TestClient

url=urlsplit(os.getenv("DATABASE_URL","").split("?",1)[0])
assert url.hostname in ("localhost","127.0.0.1") and url.path=="/marina_shared_browser_ci"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM")=="DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("APP_ENV")=="staging"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED")=="false"
assert os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED")=="true"
assert os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED")=="true"
assert os.getenv("PROPERTY_CODE")=="HOTEL_A"

from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

checks=0
def verify(value,expected,label):
    global checks
    assert value==expected,(label,value,expected)
    checks+=1

async def seed():
    conn=await asyncpg.connect(url.geturl())
    try:
        a=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_A'")
        b=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_B'")
        owner=await conn.fetchval('SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=\'owner\'',a)
        assert a and b and a!=b and owner
        expense=uuid4()
        await conn.execute(
            '''INSERT INTO owner_expenses
               (id,"propertyId","expenseDate",category,title,"amountKgs","createdById")
               VALUES($1,$2,$3,'UTILITIES','QA monthly utilities',250,$4)''',
            expense,a,date.today(),owner)
        batch=await conn.fetchrow(
            '''SELECT a.id,a."totalCostKgs" AS cost,
                      (o."completedAt" AT TIME ZONE p.timezone)::date AS day
               FROM kitchen_served_batch_allocations a
               JOIN kitchen_orders o ON o.id=a."orderId"
               JOIN properties p ON p.id=a."propertyId"
               WHERE a."propertyId"=$1 AND o.status='SERVED'
                 AND a."totalCostKgs">0 ORDER BY a.id LIMIT 1''',a)
        assert batch,"Served batch evidence required"
        return a,b,expense,batch,await conn.fetchval("SELECT count(*) FROM payments")
    finally:
        await conn.close()

a,b,expense,batch,payments_before=asyncio.run(seed())
with TestClient(app,base_url="https://owner-gl-disposable.invalid") as client:
    def login(username):
        client.post("/api/v1/auth/logout")
        r=client.post("/api/v1/auth/login",json={"username":username,"password":PASSWORD})
        verify(r.status_code,200,"authenticate "+username)

    def scenario(source_type,source_id,account_date,amount,debit,credit):
        proposal_id=str(uuid4())
        root="/api/v1/admin/finance/owner/accounting-journal/proposals"
        login("owner")
        r=client.post(root,json={
            "id":proposal_id,"source_type":source_type,"source_id":str(source_id),
            "accounting_date":account_date.isoformat(),"policy_version":"CI-GL-POLICY",
            "reason":"Independently attested business source",
            "lines":[
                {"account_code":debit,"side":"DEBIT","amount_kgs":str(amount)},
                {"account_code":credit,"side":"CREDIT","amount_kgs":str(amount)}
            ]
        })
        verify(r.status_code,201,"source proposal "+source_type)
        check_url=root+"/"+proposal_id
        verify(client.post(check_url+"/decisions",json={
            "id":str(uuid4()),"action":"APPROVE",
            "reason":"Cannot approve own proposal"
        }).status_code,403,"self approval forbidden")
        login("accounting_reviewer")
        r=client.post(check_url+"/decisions",json={
            "id":str(uuid4()),"action":"APPROVE",
            "reason":"Independently reviewed primary source and amount"
        })
        verify(r.status_code,201,"independent approval "+source_type)
        entry={"id":str(uuid4()),"action":"POST",
               "reason":"Independent approved journal posting"}
        r=client.post(check_url+"/postings",json=entry)
        verify(r.status_code,201,"post "+source_type)
        verify(r.json()["recognized_profit_kgs"],None,"no fabricated final profit")
        verify(client.post(check_url+"/postings",json=entry).json()["already_processed"],
               True,"idempotent "+source_type)
        return proposal_id

    p_expense=scenario("OPERATING_EXPENSE",expense,date.today(),250,"6000","2100")
    p_cost=scenario("STOCK_CONSUMPTION",batch["id"],batch["day"],
                    batch["cost"],"5000","1200")
    bad="/api/v1/admin/finance/owner/accounting-journal/proposals/"+str(uuid4())+"/postings"
    verify(client.post(bad,json={
        "id":str(uuid4()),"action":"POST","reason":"Cannot post a foreign source"
    }).status_code,404,"unknown property source rejected")
    r=client.get("/api/v1/admin/finance/owner/accounting-journal/posted-subtotals",
                 params={"from_date":min(date.today(),batch["day"]).isoformat(),
                         "to_date":max(date.today(),batch["day"]).isoformat()})
    verify(r.status_code,200,"subtotals")
    verify(r.json()["posted_cost_subtotal_kgs"],
           str((Decimal("250")+Decimal(batch["cost"])).quantize(Decimal("0.0001"))),
           "expense+COGS are distinct accounting costs")
    verify(r.json()["recognized_profit_kgs"],None,"no incomplete period profit")

async def verify_db():
    conn=await asyncpg.connect(url.geturl())
    try:
        verify(await conn.fetchval("SELECT count(*) FROM payments"),
               payments_before,"payment table unchanged")
        verify(await conn.fetchval(
            '''SELECT COUNT(*) FROM owner_accounting_postings p
               JOIN owner_accounting_journal_proposals j ON j.id=p."proposalId"
               WHERE p."propertyId"=$1 AND j."sourceType" IN ('OPERATING_EXPENSE','STOCK_CONSUMPTION')''',a),
            2,"exactly two posted GL sources")
        verify(await conn.fetchval(
            '''SELECT COUNT(*) FROM owner_accounting_postings p
               JOIN owner_accounting_journal_proposals j ON j.id=p."proposalId"
               WHERE p."propertyId"=$1 AND j."sourceType" IN ('OPERATING_EXPENSE','STOCK_CONSUMPTION')''',b),
            0,"other hotel entries untouched")
    finally:
        await conn.close()

asyncio.run(verify_db())
print("MARINA_OWNER_GL_EXPENSE_COGS_TWO_HOTEL_API_PASS",checks)
