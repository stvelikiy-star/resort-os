"""Two-hotel authenticated OWNER posting/reversal CI, disposable PostgreSQL only.

Synthetic source snapshots intentionally test the accounting state machine, not
real-world tax certification, service delivery, or production accounting close.
"""
import asyncio
import hashlib
import os
import uuid
from datetime import date
from urllib.parse import urlsplit

import asyncpg
from fastapi.testclient import TestClient

from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

parsed=urlsplit(os.getenv("DATABASE_URL","").split("?",1)[0])
assert parsed.hostname in ("localhost","127.0.0.1")
assert parsed.path=="/marina_shared_browser_ci"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM")=="DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("APP_ENV")=="staging"
assert os.getenv("PROPERTY_CODE")=="HOTEL_A"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED")=="false"
assert os.getenv("MARINA_ACCOUNTING_POSTING_ENABLED")=="true"
assert os.getenv("MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED")=="true"

checks=0

def check(value, expected, label):
    global checks
    assert value == expected, (label,value,expected)
    checks+=1

async def seed():
    conn=await asyncpg.connect(parsed.geturl())
    try:
        p=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_A'")
        pb=await conn.fetchval("SELECT id FROM properties WHERE code='HOTEL_B'")
        maker=await conn.fetchval(
            """SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='owner'""",p)
        reviewer=await conn.fetchval(
            """SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='accounting_reviewer'""",p)
        assert p and pb and maker and reviewer
        foreign=await conn.fetchval(
            """SELECT id FROM owner_accounting_journal_proposals
               WHERE "propertyId"=$1 LIMIT 1""",pb)
        assert foreign, "Earlier two-hotel accounting CI must run first"
        ev=uuid.uuid4()
        document_id=uuid.uuid4()
        document=b"%PDF-1.4\\n% Synthetic accounting source certification\\n%%EOF\\n"
        await conn.execute(
            """INSERT INTO owner_revenue_evidence_documents(
               id,"propertyId","documentReference","documentDate",
               "fileName","mediaType",sha256,content,"sizeBytes","uploadedById")
               VALUES($1,$2,'CI-TAX-REVIEW-700',CURRENT_DATE,
                      'synthetic-tax-ledger.pdf','application/pdf',$3,$4,$5,$6)""",
            document_id,p,hashlib.sha256(document).hexdigest(),document,len(document),maker)
        await conn.execute(
            """INSERT INTO owner_revenue_source_events
               (id,"propertyId","sourceType","sourceId","serviceDate",action,
                "faceValueKgs","sourceSnapshot",reason,"createdById")
               VALUES($1,$2,'DINING_ORDER',$3,$4,'APPROVE_SOURCE',700,
                      '{"tax_discount_refund_accounting_approved":true}'::jsonb,
                      'Synthetic two-hotel accounting posting QA',$5)""",
            ev,p,uuid.uuid4(),date.today(),maker)
        return p,pb,ev,foreign,document_id
    finally:
        await conn.close()

p,pb,source,foreign,document_id=asyncio.run(seed())
proposal=uuid.uuid4()
posting=uuid.uuid4()
with TestClient(app,base_url="https://ledger-qa.invalid") as client:
    def login(name):
        client.post("/api/v1/auth/logout")
        r=client.post("/api/v1/auth/login",json={"username":name,"password":PASSWORD})
        check(r.status_code,200,"login "+name)

    login("owner")
    base="/api/v1/admin/finance/owner/accounting-journal"
    propose={
        "id":str(proposal),"source_type":"REVENUE_SOURCE","source_id":str(source),
        "accounting_date":date.today().isoformat(),"policy_version":"CI-LEDGER-POLICY-1",
        "reason":"Independent accounting review on synthetic service source",
        "lines":[
            {"account_code":"1100","side":"DEBIT","amount_kgs":"700.0000"},
            {"account_code":"4200","side":"CREDIT","amount_kgs":"650.0000"},
            {"account_code":"2100","side":"CREDIT","amount_kgs":"50.0000"},
        ]
    }
    response=client.post(base+"/proposals",json=propose)
    check(response.status_code,201,"balanced proposal")
    check(response.json()["accounting_posted"],False,"proposal is unposted")
    owner_self=client.post(base+"/revenue-certifications",json={
        "id":str(uuid.uuid4()),"source_event_id":str(source),
        "evidence_document_id":str(document_id),"tax_amount_kgs":"50.0000",
        "policy_version":"CI-LEDGER-POLICY-1",
        "reason":"Unlawful self confirmation of own source"})
    check(owner_self.status_code,409,"source creator cannot certify own document")
    login("accounting_reviewer")
    foreign_resp=client.post(base+"/proposals/"+str(foreign)+"/post",
       json={"id":str(uuid.uuid4()),"reason":"Cross-property access must fail"})
    check(foreign_resp.status_code,404,"foreign hotel posting hidden")
    decision_url=base+"/proposals/"+str(proposal)+"/decisions"
    response=client.post(decision_url,json={
        "id":str(uuid.uuid4()),"action":"APPROVE",
        "reason":"Reviewed synthetic service tax and liability split"})
    check(response.status_code,201,"independent approval")
    url=base+"/proposals/"+str(proposal)+"/post"
    attempt_before=client.post(url,json={
        "id":str(uuid.uuid4()),"reason":"Posting without independent document must fail"})
    check(attempt_before.status_code,409,"unverified document blocks posting")
    certificate={
        "id":str(uuid.uuid4()),"source_event_id":str(source),
        "evidence_document_id":str(document_id),
        "tax_amount_kgs":"50.0000","policy_version":"CI-LEDGER-POLICY-1",
        "reason":"Independent synthetic invoice tax verification"}
    missing_doc={**certificate,"id":str(uuid.uuid4()),
                 "evidence_document_id":str(uuid.uuid4())}
    check(client.post(base+"/revenue-certifications",json=missing_doc).status_code,
          409,"unknown or foreign document denied")
    over_tax={**certificate,"id":str(uuid.uuid4()),"tax_amount_kgs":"900.0000"}
    check(client.post(base+"/revenue-certifications",json=over_tax).status_code,
          409,"certified tax cannot exceed source amount")
    certified=client.post(base+"/revenue-certifications",json=certificate)
    check(certified.status_code,201,"independent source certification")
    check(certified.json()["accounting_posted"],False,"certificate not posting")
    check(client.post(base+"/revenue-certifications",json=certificate).json()["already_processed"],
          True,"certification idempotent")
    bad_cert={**certificate,"id":str(uuid.uuid4())}
    check(client.post(base+"/revenue-certifications",json=bad_cert).status_code,
          409,"certification duplicate blocked")
    body={"id":str(posting),"reason":"Reviewed synthetic service evidence and tax split"}
    response=client.post(url,json=body)
    check(response.status_code,201,"approved posting")
    check(response.json()["accounting_posted"],True,"actual posted evidence")
    check(response.json()["recognized_profit_kgs"],None,"no false profit")
    replay=client.post(url,json=body)
    check(replay.status_code,201,"post replay")
    check(replay.json()["already_processed"],True,"posting idempotency")
    check(client.post(url,json={
        "id":str(uuid.uuid4()),"reason":"Attempt duplicate financial posting"
    }).status_code,409,"reject duplicate posting")
    profit=client.get(base+"/posted-profit",params={
       "from_date":date.today().isoformat(),"to_date":date.today().isoformat()})
    check(profit.status_code,200,"posted ledger read")
    check(profit.json()["status"],"NOT_READY","period close not verified")
    check(profit.json()["recognized_profit_kgs"],None,"unverified profit stays null")
    reverse_decision=client.post(decision_url,json={
        "id":str(uuid.uuid4()),"action":"REVERSE",
        "reason":"Independent synthetic posting cancellation review"})
    check(reverse_decision.status_code,201,"reversal decision")
    reversal_id=uuid.uuid4()
    reverse_url=base+"/postings/"+str(posting)+"/reverse"
    rev_body={"id":str(reversal_id),"reason":"Full reversal of original accounting entry"}
    response=client.post(reverse_url,json=rev_body)
    check(response.status_code,201,"exact reversal posted")
    check(client.post(reverse_url,json=rev_body).json()["already_processed"],
          True,"reversal idempotency")

async def verify():
    conn=await asyncpg.connect(parsed.geturl())
    try:
        rows=await conn.fetch(
            """SELECT action,id FROM owner_accounting_postings
               WHERE "propertyId"=$1 AND "proposalId"=$2""",p,proposal)
        check({r["action"] for r in rows},{"POST","REVERSE"},"two immutable postings")
        check(await conn.fetchval(
            """SELECT count(*) FROM owner_accounting_postings WHERE "propertyId"=$1""",pb),
            0,"foreign hotel postings untouched")
        value=await conn.fetchval(
            """SELECT COALESCE(SUM(CASE l.side WHEN 'CREDIT' THEN l."amountKgs"
                 ELSE -l."amountKgs" END),0)
               FROM owner_accounting_posting_lines l
               JOIN owner_accounting_postings p
                 ON p.id=l."postingId" AND p."propertyId"=l."propertyId"
               WHERE p."propertyId"=$1 AND l."accountCode"='4200'""",p)
        check(value,0,"original 650 KGS dining revenue exactly reversed")
        check(await conn.fetchval(
            """SELECT count(*) FROM audit_logs WHERE "propertyId"=$1
               AND action IN ('ACCOUNTING_LEDGER_POST','ACCOUNTING_LEDGER_REVERSE')""",p),
            2,"posting audit trail complete")
        try:
            await conn.execute(
                """UPDATE owner_accounting_postings SET reason='Forged mutation'
                   WHERE "propertyId"=$1 AND "proposalId"=$2""",p,proposal)
        except asyncpg.PostgresError as exc:
            check("IMMUTABLE" in str(exc),True,"posting SQL immutable")
        else:
            raise AssertionError("Posting update was allowed")
    finally:
        await conn.close()

asyncio.run(verify())
print("MARINA_OWNER_TWO_HOTEL_LEDGER_API_PASS",checks)
