"""Two-hotel immutable accounting decision API E2E; synthetic disposable CI only.

Approvals are evidence only, never a P&L posting or a money movement.
"""
import asyncio
import os
from urllib.parse import urlsplit
from uuid import uuid4

import asyncpg
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

parsed = urlsplit(os.getenv("DATABASE_URL", "").split("?", 1)[0])
assert parsed.hostname in ("127.0.0.1", "localhost")
assert parsed.path == "/marina_shared_browser_ci"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED") == "true"
assert os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED") == "true"
assert os.getenv("APP_ENV") == "staging"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "false"
assert os.getenv("PROPERTY_CODE") == "HOTEL_A"
assert os.getenv("MARINA_TENANT_CONTEXT_ENABLED") == "true"
assert os.getenv("MARINA_SHARED_BROWSER_CI_PASSWORD", "").startswith("synthetic-ci-only-")

from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

dsn = parsed.geturl()
checks = 0


def check(actual, expected, name):
    global checks
    assert actual == expected, (name, actual, expected)
    checks += 1


async def seed():
    conn = await asyncpg.connect(dsn)
    try:
        a = await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_A'")
        b = await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_B'")
        assert a and b and a != b
        creator = await conn.fetchval(
            """SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='owner'""", a)
        foreign_creator = await conn.fetchval(
            """SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='owner'""", b)
        reviewer = uuid4()
        await conn.execute(
            """INSERT INTO staff_users
               (id,"propertyId",username,"displayName","passwordHash",role,"updatedAt")
               VALUES($1,$2,'accounting_reviewer','CI Independent Reviewer',$3,'OWNER',now())""",
            reviewer, a, PasswordHasher().hash(PASSWORD))
        source_a, source_b, foreign_proposal = uuid4(), uuid4(), uuid4()
        before_payments = await conn.fetchval("SELECT count(*) FROM payments")
        async with conn.transaction():
            for property_id, source_id, author in ((a,source_a,creator),(b,source_b,foreign_creator)):
                await conn.execute(
                    """INSERT INTO owner_revenue_source_events
                       (id,"propertyId","sourceType","sourceId","serviceDate",action,
                        "faceValueKgs","sourceSnapshot",reason,"createdById")
                       VALUES($1,$2,'DINING_ORDER',$3,CURRENT_DATE,'APPROVE_SOURCE',
                              25,'{}'::jsonb,'Synthetic accounting review source',$4)""",
                    source_id, property_id, uuid4(), author)
            await conn.execute(
                """INSERT INTO owner_accounting_journal_proposals
                   (id,"propertyId","sourceType","sourceId","accountingDate","policyVersion",
                    reason,"payloadHash","createdById")
                   VALUES($1,$2,'REVENUE_SOURCE',$3,CURRENT_DATE,'CI-EVIDENCE-01',
                          'Synthetic foreign proposal',repeat('e',64),$4)""",
                foreign_proposal, b, source_b, foreign_creator)
            await conn.execute(
                """INSERT INTO owner_accounting_journal_proposal_lines
                   ("proposalId","propertyId","lineNo","accountCode",side,"amountKgs")
                   VALUES($1,$2,1,'1000','DEBIT',25),
                         ($1,$2,2,'4000','CREDIT',25)""", foreign_proposal, b)
        return a, b, source_a, foreign_proposal, before_payments
    finally:
        await conn.close()


a, b, source_a, foreign_proposal, payments_before = asyncio.run(seed())

with TestClient(app, base_url="https://accounting-disposable.invalid") as client:
    def login(username):
        client.post("/api/v1/auth/logout")
        r = client.post("/api/v1/auth/login",
                        json={"username":username,"password":PASSWORD})
        check(r.status_code, 200, "login " + username)

    login("owner")
    proposal_id = str(uuid4())
    proposal_body = {
        "id": proposal_id,
        "source_type": "REVENUE_SOURCE", "source_id": str(source_a),
        "accounting_date": __import__("datetime").date.today().isoformat(),
        "policy_version": "CI-EVIDENCE-01",
        "reason": "Reviewed synthetic source evidence only",
        "lines": [
            {"account_code":"1100","side":"DEBIT","amount_kgs":"25.0000"},
            {"account_code":"4100","side":"CREDIT","amount_kgs":"25.0000"},
        ],
    }
    r = client.post("/api/v1/admin/finance/owner/accounting-journal/proposals",
                    json=proposal_body)
    check(r.status_code, 201, "original proposal")
    check(r.json()["accounting_posted"], False, "proposal not posted")

    url = "/api/v1/admin/finance/owner/accounting-journal/proposals/" + proposal_id + "/decisions"
    foreign = "/api/v1/admin/finance/owner/accounting-journal/proposals/" + str(foreign_proposal) + "/decisions"
    check(client.get(foreign).status_code, 404, "foreign proposal read")
    check(client.post(foreign, json={
        "id":str(uuid4()),"action":"APPROVE","reason":"Cross-property attempt"
    }).status_code, 404, "foreign proposal approve")

    body = {"id":str(uuid4()),"action":"APPROVE",
            "reason":"Independent confirmed source and balances"}
    check(client.post(url, json=body).status_code, 403, "no self approval")

    login("accounting_reviewer")
    r = client.post(url, json=body)
    check(r.status_code, 201, "independent approval")
    check(r.json()["accounting_posted"], False, "approval is not posting")
    r = client.post(url, json=body)
    check(r.status_code, 201, "approval replay status")
    check(r.json()["already_processed"], True, "approval replay idempotent")
    check(client.post(url,json={**body,"id":str(uuid4())}).status_code,
          409,"duplicate independent approval rejected")
    r = client.get(url)
    check(r.status_code, 200, "approved readback")
    check(r.json()["evidence_status"], "EVIDENCE_APPROVED", "approved state")
    posting_url = "/api/v1/admin/finance/owner/accounting-journal/proposals/" + proposal_id + "/postings"
    foreign_post = "/api/v1/admin/finance/owner/accounting-journal/proposals/" + str(foreign_proposal) + "/postings"
    check(client.get(foreign_post).status_code,404,"foreign hotel posting denied")
    check(client.post(foreign_post,json={"id":str(uuid4()),"action":"POST",
        "reason":"Foreign hotel attempt blocked"}).status_code,404,"foreign posting write denied")
    posting={"id":str(uuid4()),"action":"POST","reason":"Independent posted service evidence"}
    r=client.post(posting_url,json=posting)
    check(r.status_code,201,"POST approved exact revenue proposal")
    check(r.json()["accounting_posted"],True,"real posting written")
    check(r.json()["recognized_profit_kgs"],None,"no premature profit after POST")
    r=client.post(posting_url,json=posting)
    check(r.status_code,201,"posted replay status")
    check(r.json()["already_processed"],True,"posted event is idempotent")
    check(client.post(posting_url,json={**posting,"id":str(uuid4())}).status_code,
          409,"second POST blocked")
    subtotal_url="/api/v1/admin/finance/owner/accounting-journal/posted-subtotals"
    period={"from_date":__import__("datetime").date.today().isoformat(),
            "to_date":__import__("datetime").date.today().isoformat()}
    r=client.get(subtotal_url,params=period)
    check(r.status_code,200,"posting subtotal read")
    check(r.json()["posted_revenue_subtotal_kgs"],"25.0000","gross posted source value")
    check(r.json()["recognized_profit_kgs"],None,"subtotal is not full profit")
    reversing={"id":str(uuid4()),"action":"REVERSE",
               "reason":"Independent exact GL posting reversal"}
    r=client.post(posting_url,json=reversing)
    check(r.status_code,201,"GL reversal posted")
    check(r.json()["accounting_posted"],True,"reversal is recorded")
    r=client.get(subtotal_url,params=period)
    check(r.status_code,200,"reversed subtotal read")
    check(r.json()["posted_revenue_subtotal_kgs"],"0.0000","balanced GL reversal restores zero")
    check(client.get(posting_url).json()["items"].__len__(),2,"both posting events preserved")
    reversal = {"id":str(uuid4()),"action":"REVERSE",
                "reason":"Independent review correction required"}
    r = client.post(url, json=reversal)
    check(r.status_code, 201, "reversal")
    r = client.get(url)
    check(r.status_code, 200, "reversed readback")
    check(r.json()["evidence_status"], "EVIDENCE_REVERSED", "reversed state")
    check(r.json()["recognized_profit_kgs"], None, "no invented profit")
    check(r.json()["accounting_posted"], False, "decision endpoint is evidence only")

async def verify():
    conn=await asyncpg.connect(dsn)
    try:
        check(await conn.fetchval("SELECT count(*) FROM owner_accounting_postings WHERE \"propertyId\"=$1",a),2,"two immutable GL events")
        check(await conn.fetchval("SELECT count(*) FROM owner_accounting_postings WHERE \"propertyId\"=$1",b),0,"other hotel GL untouched")
        check(await conn.fetchval("SELECT count(*) FROM payments"),
              payments_before, "no payments created")
        check(await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_journal_decisions
               WHERE "propertyId"=$1 AND "proposalId"=$2""",
            a, __import__("uuid").UUID(proposal_id)), 2, "two immutable decisions")
        check(await conn.fetchval(
            'SELECT count(*) FROM owner_accounting_journal_decisions WHERE "propertyId"=$1',
            b),0,"other hotel's decisions untouched")
        check(await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_journal_proposals
               WHERE id=$1 AND status='PENDING_ACCOUNTANT_APPROVAL'""",
            __import__("uuid").UUID(proposal_id)),1,"proposal remains pending posting")
    finally:
        await conn.close()

asyncio.run(verify())
print("MARINA_ACCOUNTING_POSTED_GL_TWO_HOTEL_API_PASS",checks)
