"""Isolated two-hotel OWNER non-stock expense posting and reversal acceptance."""
import asyncio
import os
import uuid
from datetime import date
from urllib.parse import urlsplit
import asyncpg
from fastapi.testclient import TestClient

from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

u=urlsplit(os.environ.get("DATABASE_URL","").split("?",1)[0])
assert u.hostname in ("localhost","127.0.0.1") and u.path=="/marina_shared_browser_ci"
assert os.environ.get("APP_ENV")=="staging"
assert os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM")=="DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.environ.get("MARINA_ACCOUNTING_POSTING_ENABLED")=="true"
assert os.environ.get("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED")=="true"
assert os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED")=="false"
assert os.environ.get("PROPERTY_CODE")=="HOTEL_A"

checks=0
def check(actual,expected,label):
    global checks
    assert actual==expected,(label,actual,expected)
    checks+=1

async def seed():
    conn=await asyncpg.connect(u.geturl())
    try:
        pid=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_A'")
        owner=await conn.fetchval(
            """SELECT id FROM staff_users WHERE "propertyId"=$1
               AND username='owner'""",pid)
        assert pid and owner
        expense=uuid.uuid4()
        stock=uuid.uuid4()
        await conn.execute(
            """INSERT INTO owner_expenses
               (id,"propertyId","expenseDate",category,title,"amountKgs",
                "supplierName","documentReference",status,"createdById")
               VALUES($1,$2,CURRENT_DATE,'UTILITIES','Synthetic electricity',250,
                      'Synthetic Utility CI','CI-UTILITY-001','POSTED',$3)""",
            expense,pid,owner)
        await conn.execute(
            """INSERT INTO owner_expenses
               (id,"propertyId","expenseDate",category,title,"amountKgs",
                "supplierName","documentReference",status,"createdById")
               VALUES($1,$2,CURRENT_DATE,'SUPPLIES','Synthetic kitchen supplies',1200,
                      'Synthetic Supply CI','CI-STOCK-001','POSTED',$3)""",
            stock,pid,owner)
        return pid,expense,stock
    finally:
        await conn.close()

property_id,expense,stock=asyncio.run(seed())
proposal_id=uuid.uuid4()
posting_id=uuid.uuid4()
base="/api/v1/admin/finance/owner/accounting-journal"
with TestClient(app,base_url="https://owner-expense-disposable.invalid") as client:
    def login(username):
        client.post("/api/v1/auth/logout")
        r=client.post("/api/v1/auth/login",json={
           "username":username,"password":PASSWORD})
        check(r.status_code,200,"login "+username)

    login("owner")
    body={"id":str(proposal_id),"source_type":"OPERATING_EXPENSE",
          "source_id":str(expense),"accounting_date":date.today().isoformat(),
          "policy_version":"CI-EXPENSE-1",
          "reason":"Documented independent non-stock utilities invoice",
          "lines":[
             {"account_code":"5200","side":"DEBIT","amount_kgs":"250.0000"},
             {"account_code":"2200","side":"CREDIT","amount_kgs":"250.0000"}]}
    r=client.post(base+"/proposals",json=body)
    check(r.status_code,201,"utility expense proposal")
    check(r.json()["accounting_posted"],False,"proposal does not book expense")
    unsafe=client.post(base+"/proposals",json={
        **body,"id":str(uuid.uuid4()),"source_id":str(stock),
        "reason":"Stock supplies must be rejected as period expense"})
    check(unsafe.status_code,409,"warehouse supplies rejected")

    # Created-by owner may not independently approve or post.
    proposal_path=base+"/proposals/"+str(proposal_id)
    r=client.post(proposal_path+"/post",json={
      "id":str(uuid.uuid4()),"reason":"Self approved entry should fail"})
    check(r.status_code,403,"self posting denied")
    login("accounting_reviewer")
    decision=client.post(proposal_path+"/decisions",json={
      "id":str(uuid.uuid4()),"action":"APPROVE",
      "reason":"Independently confirmed utility invoice and date"})
    check(decision.status_code,201,"expense independent approval")
    posted={"id":str(posting_id),
            "reason":"Document-backed independent expense posting"}
    result=client.post(proposal_path+"/post",json=posted)
    check(result.status_code,201,"nonstock expense posting")
    check(result.json()["accounting_posted"],True,"posting persisted")
    check(result.json()["recognized_profit_kgs"],None,"profit still not complete")
    replay=client.post(proposal_path+"/post",json=posted)
    check(replay.status_code,201,"posting replay 201")
    check(replay.json()["already_processed"],True,"idempotent posting")
    new_id=client.post(proposal_path+"/post",json={
      "id":str(uuid.uuid4()),"reason":"New posting ID must not double count"})
    check(new_id.status_code,409,"second invoice posting rejected")

    reversal_decision=client.post(proposal_path+"/decisions",json={
      "id":str(uuid.uuid4()),"action":"REVERSE",
      "reason":"Independent reversal of test utility invoice"})
    check(reversal_decision.status_code,201,"reversal decision")
    reversal={"id":str(uuid.uuid4()),
              "reason":"Exact credit and debit utility expense reversal"}
    reversed_response=client.post(base+"/postings/"+str(posting_id)+"/reverse",
                                 json=reversal)
    check(reversed_response.status_code,201,"exact expense reversal")
    check(client.post(base+"/postings/"+str(posting_id)+"/reverse",
                      json=reversal).json()["already_processed"],
          True,"expense reversal idempotent")
    statement=client.get(base+"/posted-profit",params={
      "from_date":date.today().isoformat(),
      "to_date":date.today().isoformat()})
    check(statement.status_code,200,"post reversal reporting route")
    check(statement.json()["recognized_profit_kgs"],None,
          "no invented recognized profit before complete close")

async def verify():
    conn=await asyncpg.connect(u.geturl())
    try:
        count=await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_postings
               WHERE "propertyId"=$1 AND "proposalId"=$2""",
            property_id,proposal_id)
        check(count,2,"original plus reversal")
        balance=await conn.fetchval(
            """SELECT COALESCE(SUM(CASE WHEN l.side='DEBIT' THEN l."amountKgs"
                                       ELSE -l."amountKgs" END),0)
               FROM owner_accounting_posting_lines l
               JOIN owner_accounting_postings p ON p.id=l."postingId"
                 AND p."propertyId"=l."propertyId"
               WHERE p."propertyId"=$1 AND p."proposalId"=$2
                 AND l."accountCode"='5200'""",property_id,proposal_id)
        check(balance,0,"utility expense reversed to zero")
        foreign=await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_postings p
               JOIN properties h ON h.id=p."propertyId"
               WHERE h.code='HOTEL_B'""")
        check(foreign,0,"HOTEL_B remains untouched")
    finally:
        await conn.close()

asyncio.run(verify())
print("MARINA_OWNER_EXPENSE_POST_REVERSE_TWO_HOTEL_PASS",checks)
