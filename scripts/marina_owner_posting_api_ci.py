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
    tax_id=uuid.uuid4()
    # Same stored invoice bytes; the reviewer must approve the exact amount.
    doc_bytes=b"%PDF-1.4\\n% Synthetic accounting source certification\\n%%EOF\\n"
    tax_event={
        "id":str(tax_id),"approval_id":str(source),"kind":"TAX_COMPONENT",
        "component":"DINING","amount_kgs":"50.0000",
        "document_reference":"CI-TAX-REVIEW-700","document_date":date.today().isoformat(),
        "document_sha256":hashlib.sha256(doc_bytes).hexdigest(),
        "evidence_document_id":str(document_id),"evidence_reference":"Synthetic original invoice",
        "reason":"Record documented tax allocation for source"
    }
    check(client.post("/api/v1/admin/finance/owner/revenue-corrections",json=tax_event).status_code,
          201,"document-backed tax correction")
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
    wrong_tax={**certificate,"id":str(uuid.uuid4()),"tax_amount_kgs":"49.0000"}
    check(client.post(base+"/revenue-certifications",json=wrong_tax).status_code,
          409,"tax certificate cannot differ from documented correction")
    certified=client.post(base+"/revenue-certifications",json=certificate)
    check(certified.status_code,201,"independent source certification")
    check(certified.json()["accounting_posted"],False,"certificate not posting")
    check(client.post(base+"/revenue-certifications",json=certificate).json()["already_processed"],
          True,"certification idempotent")
    bad_cert={**certificate,"id":str(uuid.uuid4())}
    check(client.post(base+"/revenue-certifications",json=bad_cert).status_code,
          409,"certification duplicate blocked")
    body={"id":str(posting),"reason":"Reviewed synthetic service evidence and tax split"}
    async def verify_wrong_date():
        from datetime import timedelta
        from app.owner_accounting_postings import qualified_posting_source
        from fastapi import HTTPException
        conn=await asyncpg.connect(parsed.geturl())
        try:
            async with conn.transaction():
                q=await conn.fetchrow('SELECT * FROM owner_accounting_journal_proposals WHERE id=$1',proposal)
                try:
                    await qualified_posting_source(conn,p,{**dict(q),"accountingDate":date.today()-timedelta(days=1)})
                except HTTPException as exc:
                    check(exc.status_code,409,"wrong service date rejected")
                    check(exc.detail["code"],"ACCOUNTING_REVENUE_SERVICE_DATE_MISMATCH","specific date error")
                else:
                    raise AssertionError("Wrong accounting date accepted")
        finally:
            await conn.close()
    asyncio.run(verify_wrong_date())
    response=client.post(url,json=body)
    check(response.status_code,201,"approved posting")
    check(response.json()["accounting_posted"],True,"actual posted evidence")
    async def verify_tax_binding():
        conn=await asyncpg.connect(parsed.geturl())
        try:
            bound=await conn.fetchval("""SELECT "taxCorrectionEventId"
              FROM owner_revenue_accounting_certifications
              WHERE "propertyId"=$1 AND "sourceEventId"=$2""",p,source)
            check(bound,tax_id,"immutable document tax-event binding")
            lines=await conn.fetch("""SELECT "accountCode",side,"amountKgs"
              FROM owner_accounting_posting_lines WHERE "postingId"=$1""",posting)
            check(sorted((r["accountCode"],r["side"],int(r["amountKgs"])) for r in lines),
                  [("1100","DEBIT",700),("2100","CREDIT",50),("4200","CREDIT",650)],
                  "tax allocation recognized exactly once")
            match="SELECT owner_revenue_corrections_match_certificate($1,$2,$3,$4,$5,$6)"
            reviewer=await conn.fetchval("""SELECT id FROM staff_users
                WHERE "propertyId"=$1 AND username='accounting_reviewer'""",p)
            check(await conn.fetchval(match,p,source,document_id,reviewer,50,tax_id),True,"exact binding valid")
            check(await conn.fetchval(match,p,source,document_id,reviewer,49,tax_id),False,"wrong tax rejected")
            check(await conn.fetchval(match,pb,source,document_id,reviewer,50,tax_id),False,"foreign tax rejected")
            check(await conn.fetchval(match,p,source,document_id,reviewer,50,None),False,"unbound active tax rejected")
        finally:
            await conn.close()
    asyncio.run(verify_tax_binding())
    correction_reverse="/api/v1/admin/finance/owner/revenue-corrections/"+str(tax_id)+"/reverse"
    check(client.post(correction_reverse,json={"id":str(uuid.uuid4()),
        "reason":"Cannot reverse tax while revenue is posted"}).status_code,409,
        "posted tax cannot be reversed alone")
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
    source_reverse_url="/api/v1/admin/finance/owner/revenue-source-events/"+str(source)+"/reverse"
    source_reverse_body={"id":str(uuid.uuid4()),"reason":"Cancel source after exact ledger reversal"}
    denied=client.post(source_reverse_url,json=source_reverse_body)
    check(denied.status_code,409,"active ledger blocks source reversal")
    check(denied.json()["detail"]["code"],"OWNER_REVENUE_ACTIVE_POSTING_REQUIRES_REVERSAL","specific source guard")
    async def direct_source_reversal_denied():
        conn=await asyncpg.connect(parsed.geturl())
        try:
            try:
                await conn.execute(
                    """INSERT INTO owner_revenue_source_events
                       (id,"propertyId","sourceType","sourceId","serviceDate",action,
                        "faceValueKgs","sourceSnapshot","reversesId",reason,"createdById")
                       SELECT $1,"propertyId","sourceType","sourceId","serviceDate",'REVERSE_SOURCE',
                         "faceValueKgs","sourceSnapshot",id,'Direct SQL cancellation attempt',"createdById"
                       FROM owner_revenue_source_events WHERE id=$2 AND "propertyId"=$3""",
                    uuid.uuid4(),source,p)
            except asyncpg.CheckViolationError as exc:
                check("OWNER_REVENUE_ACTIVE_POSTING_REQUIRES_REVERSAL" in str(exc),True,"SQL cannot bypass guard")
            else:
                raise AssertionError("Direct SQL reversed posted source")
        finally:
            await conn.close()
    asyncio.run(direct_source_reversal_denied())
    coverage=client.get(base+"/period-coverage",params={"from_date":date.today().isoformat(),"to_date":date.today().isoformat()})
    check(coverage.status_code,200,"period coverage diagnostic")
    check(coverage.json()["period_completeness_verified"],False,"coverage cannot close period")
    check(coverage.json()["recognized_profit_kgs"],None,"coverage does not fabricate profit")
    dates={"from_date":date.today().isoformat(),"to_date":date.today().isoformat()}
    summary_url="/api/v1/admin/finance/summary"
    enabled_summary=client.get(summary_url,params=dates)
    check(enabled_summary.status_code,200,"owner summary with accounting enabled")
    check(enabled_summary.json()["owner_ledger_period_coverage"],coverage.json(),"summary embeds same period coverage")
    try:
        os.environ["MARINA_ACCOUNTING_POSTING_ENABLED"]="false"
        disabled_summary=client.get(summary_url,params=dates)
        check(disabled_summary.status_code,200,"legacy finance summary remains available")
        check("owner_ledger_period_coverage" in disabled_summary.json(),False,"no ledger when guard disabled")
        check(client.get(base+"/period-coverage",params=dates).status_code,503,"direct API guard preserved")
    finally:
        os.environ["MARINA_ACCOUNTING_POSTING_ENABLED"]="true"
    check(coverage.json()["period"],{"from":date.today().isoformat(),"to":date.today().isoformat()},"coverage date range")
    for name in ("package_entitlement_count","package_portions_count","refund_payment_expected",
                 "refund_payment_verified","refund_undated_count"):
        check(isinstance(coverage.json()["counts"][name],int),True,"coverage counter "+name)
    check(coverage.json()["posted_ledger_subtotals"]["posting_line_count"]>0,True,"posted totals and coverage share snapshot")
    check(coverage.json()["counts"]["unmatched_approved_sources"]>0,True,"synthetic approval not mistaken for delivered source")
    check("APPROVED_SOURCE_NOT_MATCHED_TO_DELIVERY" in coverage.json()["blockers"],True,"unmatched source blocker")
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
    check(client.post(correction_reverse,json={"id":str(uuid.uuid4()),
        "reason":"Reverse documented tax after exact ledger reversal"}).status_code,201,
        "tax reversal permitted after ledger reversal")
    check(client.post(source_reverse_url,json=source_reverse_body).status_code,201,
          "source reversal allowed after exact ledger reversal")
    check(client.post(source_reverse_url,json=source_reverse_body).json()["already_processed"],
          True,"source reversal replay")
    check(client.post(source_reverse_url,json={**source_reverse_body,"id":str(uuid.uuid4())}).status_code,
          409,"duplicate source reversal blocked")

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

# Actual competing SQL writers against the existing immutable journal.
# Fixtures use only the disposable CI database, and winning postings are
# exactly reversed before later financial tests run.
async def race_fixture(conn):
    sid,qid,did=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
    reviewer=await conn.fetchval(
        """SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='accounting_reviewer'""",p)
    await conn.execute(
        """INSERT INTO owner_revenue_source_events
           (id,"propertyId","sourceType","sourceId","serviceDate",action,
            "faceValueKgs","sourceSnapshot",reason,"createdById")
           SELECT $1,"propertyId","sourceType",$2,"serviceDate",action,
                  "faceValueKgs","sourceSnapshot",'Concurrent isolated source fixture',"createdById"
           FROM owner_revenue_source_events WHERE id=$3 AND "propertyId"=$4""",
        sid,uuid.uuid4(),source,p)
    await conn.execute(
        """INSERT INTO owner_accounting_journal_proposals
           (id,"propertyId","sourceType","sourceId","accountingDate","policyVersion",reason,"payloadHash","createdById")
           SELECT $1,"propertyId","sourceType",$2,"accountingDate","policyVersion",
                  'Concurrent isolated proposal fixture',$3,"createdById"
           FROM owner_accounting_journal_proposals WHERE id=$4 AND "propertyId"=$5""",
        qid,sid,hashlib.sha256(str(qid).encode()).hexdigest(),proposal,p)
    await conn.execute(
        """INSERT INTO owner_accounting_journal_proposal_lines
           ("proposalId","propertyId","lineNo","accountCode",side,"amountKgs")
           SELECT $1,"propertyId","lineNo","accountCode",side,"amountKgs"
           FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$2 AND "propertyId"=$3""",
        qid,proposal,p)
    await conn.execute(
        """INSERT INTO owner_accounting_journal_decisions
           (id,"propertyId","proposalId",action,"actorId",reason)
           VALUES($1,$2,$3,'APPROVE',$4,'Concurrent isolated approval fixture')""",
        did,p,qid,reviewer)
    await conn.execute(
        """INSERT INTO owner_revenue_accounting_certifications
           (id,"propertyId","sourceEventId","evidenceDocumentId","reviewedById",
            "grossAmountKgs","taxAmountKgs","netRevenueKgs","policyVersion",reason)
           SELECT $1,"propertyId",$2,"evidenceDocumentId","reviewedById",
                  "grossAmountKgs","taxAmountKgs","netRevenueKgs","policyVersion",
                  'Concurrent isolated document certification'
           FROM owner_revenue_accounting_certifications
           WHERE "propertyId"=$3 AND "sourceEventId"=$4""",
        uuid.uuid4(),sid,p,source)
    return sid,qid,did,reviewer

async def race_post(conn,fixture):
    sid,qid,did,reviewer=fixture
    post_id=uuid.uuid4()
    await conn.execute(
        """INSERT INTO owner_accounting_postings
           (id,"propertyId","proposalId","decisionId",action,"accountingDate",
            "policyVersion","postedById","sourceCompletenessAttested",reason)
           SELECT $1,"propertyId",id,$2,'POST',"accountingDate","policyVersion",$3,true,
                  'Concurrent isolated accounting posting'
           FROM owner_accounting_journal_proposals WHERE id=$4 AND "propertyId"=$5""",
        post_id,did,reviewer,qid,p)
    await conn.execute(
        """INSERT INTO owner_accounting_posting_lines
           ("postingId","propertyId","lineNo","accountCode",side,"amountKgs")
           SELECT $1,"propertyId","lineNo","accountCode",side,"amountKgs"
           FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$2 AND "propertyId"=$3""",
        post_id,qid,p)

async def race_reverse(conn,fixture):
    await conn.execute(
        """INSERT INTO owner_revenue_source_events
           (id,"propertyId","sourceType","sourceId","serviceDate",action,
            "faceValueKgs","sourceSnapshot","reversesId",reason,"createdById")
           SELECT $1,"propertyId","sourceType","sourceId","serviceDate",'REVERSE_SOURCE',
                  "faceValueKgs","sourceSnapshot",id,'Concurrent isolated source reversal',"createdById"
           FROM owner_revenue_source_events WHERE id=$2 AND "propertyId"=$3""",
        uuid.uuid4(),fixture[0],p)

async def clean_race_post(conn,fixture):
    sid,qid,did,reviewer=fixture
    original=await conn.fetchval(
        """SELECT id FROM owner_accounting_postings
           WHERE "propertyId"=$1 AND "proposalId"=$2 AND action='POST'""",p,qid)
    rd,rid=uuid.uuid4(),uuid.uuid4()
    await conn.execute(
        """INSERT INTO owner_accounting_journal_decisions
           (id,"propertyId","proposalId",action,"approvalId","actorId",reason)
           VALUES($1,$2,$3,'REVERSE',$4,$5,'Concurrent fixture exact reversal')""",
        rd,p,qid,did,reviewer)
    await conn.execute(
        """INSERT INTO owner_accounting_postings
           (id,"propertyId","proposalId","decisionId",action,"reversesId",
            "accountingDate","policyVersion","postedById","sourceCompletenessAttested",reason)
           SELECT $1,"propertyId","proposalId",$2,'REVERSE',id,
                  "accountingDate","policyVersion",$3,true,'Concurrent fixture exact reversal'
           FROM owner_accounting_postings WHERE id=$4 AND "propertyId"=$5""",
        rid,rd,reviewer,original,p)
    await conn.execute(
        """INSERT INTO owner_accounting_posting_lines
           ("postingId","propertyId","lineNo","accountCode",side,"amountKgs")
           SELECT $1,"propertyId","lineNo","accountCode",
                  CASE WHEN side='DEBIT' THEN 'CREDIT' ELSE 'DEBIT' END,"amountKgs"
           FROM owner_accounting_posting_lines WHERE "postingId"=$2 AND "propertyId"=$3""",
        rid,original,p)
    await race_reverse(conn,fixture)

async def verify_concurrency():
    setup=await asyncpg.connect(parsed.geturl())
    a=await asyncpg.connect(parsed.geturl())
    b=await asyncpg.connect(parsed.geturl())
    try:
        for isolation in ("read_committed","repeatable_read"):
            for post_first in (True,False):
                async with setup.transaction():
                    fixture=await race_fixture(setup)
                first,second=(race_post,race_reverse) if post_first else (race_reverse,race_post)
                ta=a.transaction(isolation=isolation)
                tb=b.transaction(isolation=isolation)
                await ta.start()
                await tb.start()
                contender=None
                try:
                    await b.fetchval("SELECT count(*) FROM owner_revenue_source_events")
                    await first(a,fixture)
                    contender=asyncio.create_task(second(b,fixture))
                    for _ in range(200):
                        if a.get_server_pid() in await setup.fetchval(
                            "SELECT pg_blocking_pids($1)",b.get_server_pid()):
                            break
                        if contender.done():
                            await contender
                            raise AssertionError("Contender completed without waiting")
                        await asyncio.sleep(0.025)
                    else:
                        raise AssertionError("Expected PostgreSQL contention not observed")
                    check(True,True,"contender blocked on actual transaction")
                    await ta.commit()
                    try:
                        await asyncio.wait_for(contender,10)
                    except asyncpg.PostgresError as exc:
                        expected=("OWNER_REVENUE_ACTIVE_POSTING_REQUIRES_REVERSAL"
                                  if post_first else "OWNER_REVENUE_SOURCE_ALREADY_REVERSED")
                        check((isolation=="repeatable_read" and exc.sqlstate=="40001") or
                              (exc.sqlstate=="23514" and expected in str(exc)),True,
                              "conflicting operation rejected after winner commits")
                    else:
                        raise AssertionError("Conflicting operation succeeded")
                finally:
                    if contender is not None and not contender.done():
                        contender.cancel()
                        await asyncio.gather(contender,return_exceptions=True)
                    if b.is_in_transaction():
                        await tb.rollback()
                    if a.is_in_transaction():
                        await ta.rollback()
                sid=fixture[0]
                check(await setup.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),
                      post_first,"only winning ledger state")
                check(await setup.fetchval(
                    """SELECT EXISTS(SELECT 1 FROM owner_revenue_source_events
                       WHERE "propertyId"=$1 AND "reversesId"=$2 AND action='REVERSE_SOURCE')""",p,sid),
                    not post_first,"only winning source state")
                if post_first:
                    async with setup.transaction():
                        await clean_race_post(setup,fixture)
                check(await setup.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),
                      False,"race fixture has no outstanding ledger")
        check(await setup.fetchval(
            """SELECT count(*) FROM owner_accounting_postings WHERE "propertyId"=$1""",pb),
            0,"concurrent fixtures preserve hotel B")
    finally:
        await a.close()
        await b.close()
        await setup.close()

before_concurrency=checks
asyncio.run(verify_concurrency())
print("MARINA_OWNER_CONCURRENT_POST_REVERSE_PASS",checks-before_concurrency)

# 600 nights across two valid completed stays: the public preview stays
# bounded but every qualified night is delivered to financial reconciliation.
async def verify_full_lodging_iteration():
    from datetime import timedelta
    from app.owner_delivered_revenue import delivered_sources, PREVIEW_LIMIT
    start=date(2025,1,1)
    end=start+timedelta(days=300)
    reservations=[{
        "id":uuid.uuid4(),"reservation_status":"CHECKED_OUT","stay_count":1,
        "stay_status":"CHECKED_OUT","actual_in":start,"actual_out":end,
        "has_room_assignment":True,"checkIn":start,"checkOut":end,"totalKgs":300001,
    } for _ in range(2)]
    class ReadFixture:
        async def fetch(self,sql,*args):
            if "FROM reservations r" in sql:
                return reservations
            if "FROM kitchen_orders o" in sql:
                return []
            raise AssertionError(sql)
        async def fetchrow(self,sql,*args):
            return {"charge_count":0,"face_value":0}
        async def fetchval(self,sql,*args):
            return 0
    observed=[]
    result=await delivered_sources(ReadFixture(),p,start,end,"Asia/Bishkek",
                                   on_night=lambda rid,day,amount:observed.append((rid,day,amount)))
    room=result["accommodation"]
    check(room["delivered_booked_nights_count"],600,"all delivered nights counted")
    check(len(observed),600,"all nights reach accounting observer")
    check(len({(rid,day) for rid,day,_ in observed}),600,"unique nightly source identity")
    check(sum(amount for _,_,amount in observed),600002,"exact nightly gross preserved")
    check(len(room["night_preview"]),PREVIEW_LIMIT,"UI preview remains bounded")
    check(room["night_preview_truncated"],True,"UI truncation reported")
    check(observed[-1][1],end-timedelta(days=1),"last night beyond preview reconciled")
before_lodging=checks
asyncio.run(verify_full_lodging_iteration())
print("MARINA_OWNER_FULL_LODGING_ITERATION_PASS",checks-before_lodging)

# Direct SQL guard exists in the new additive migration, independent of API.
async def verify_period_guards():
    conn=await asyncpg.connect(parsed.geturl())
    try:
        triggers=await conn.fetch("""SELECT tgname FROM pg_trigger
            WHERE NOT tgisinternal AND tgname IN
            ('ab_owner_revenue_period_posting','aa_owner_correction_posting_guard')""")
        check(len(triggers),2,"both PostgreSQL period guards installed")
        async with conn.transaction():
            fixture=await race_fixture(conn)
            # Run direct INSERT with a mismatched header against the new trigger.
            # The earlier proposal/header integrity guard may also reject it.
            from datetime import timedelta
            q=await conn.fetchrow('SELECT * FROM owner_accounting_journal_proposals WHERE id=$1',fixture[1])
            try:
                async with conn.transaction():
                    await conn.execute("""INSERT INTO owner_accounting_postings
                        (id,"propertyId","proposalId","decisionId",action,"accountingDate",
                         "policyVersion","postedById","sourceCompletenessAttested",reason)
                        VALUES($1,$2,$3,$4,'POST',$5,$6,$7,true,'Direct wrong date test')""",
                        uuid.uuid4(),p,fixture[1],fixture[2],
                        q["accountingDate"]-timedelta(days=1),q["policyVersion"],fixture[3])
            except asyncpg.CheckViolationError as exc:
                check("ACCOUNTING_REVENUE_SERVICE_DATE_MISMATCH" in str(exc),True,
                      "direct SQL wrong service date rejected")
            else:
                raise AssertionError("wrong service date accepted")
            # Keep fixture isolated; no artificial posting is accepted.
    finally:
        await conn.close()
before_period=checks
asyncio.run(verify_period_guards())
print("MARINA_OWNER_PERIOD_SQL_GUARDS_PASS",checks-before_period)

# Actual task/folio, independent certificate and exact SQL posting; rolled
# back after checking deferred constraints. No production connections.
async def verify_guest_service_ledger(*, mutation_checks=False, refund_checks=False):
    from datetime import timedelta
    conn=await asyncpg.connect(parsed.geturl())
    tx=conn.transaction()
    await tx.start()
    try:
        maker=await conn.fetchval("""SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='owner'""",p)
        reviewer=await conn.fetchval("""SELECT id FROM staff_users WHERE "propertyId"=$1 AND username='accounting_reviewer'""",p)
        # This workflow runs before browser stay creation. Create its own
        # real relational fixture in the same rolled-back transaction.
        day=await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1",p)
        gid,rid,stay_id=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
        await conn.execute("""INSERT INTO guests (id,"propertyId","firstName","lastName","createdAt","updatedAt")
            VALUES($1,$2,'CI','Guest service',now(),now())""",gid,p)
        await conn.execute("""INSERT INTO reservations
            (id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,"totalKgs","createdAt","updatedAt")
            VALUES($1,$2,$3,$4,'CHECKED_IN',$5,$6,1,2000,now(),now())""",
            rid,p,"CI-GUEST-"+str(rid),gid,day,day+timedelta(days=1))
        await conn.execute("""INSERT INTO stays
            (id,"propertyId","reservationId","guestId",status,"actualCheckInAt","createdAt","updatedAt")
            VALUES($1,$2,$3,$4,'ACTIVE',now() AT TIME ZONE 'UTC',now(),now())""",stay_id,p,rid,gid)
        stay={"id":stay_id,"reservationId":rid,"guestId":gid}
        tid,fid,sid,qid,did=([uuid.uuid4() for _ in range(5)])
        await conn.execute("""INSERT INTO operational_tasks
          (id,"propertyId","reservationId","stayId","serviceCode","serviceDate",type,status,priority,
           title,"createdByType","createdById","completedAt","createdAt","updatedAt",
           "chargeKgs","chargeStatus","chargeSource")
          VALUES($1,$2,$3,$4,'LINEN',$5,'GUEST_REQUEST','DONE','NORMAL',
           'Synthetic guest service accounting','STAFF',$6,now() AT TIME ZONE 'UTC',now(),now(),700,'POSTED','FOLIO')""",
          tid,p,stay["reservationId"],stay["id"],day,str(maker))
        await conn.execute("""INSERT INTO guest_folio_charges
          (id,"propertyId","reservationId","stayId","guestId","sourceType","sourceId",code,
           description,"amountKgs",status,"serviceDate","createdByType","createdById")
          VALUES($1,$2,$3,$4,$5,'GUEST_SERVICE',$6,'LINEN','Synthetic matched service',700,'OPEN',$7,'STAFF',$8)""",
          fid,p,stay["reservationId"],stay["id"],stay["guestId"],tid,day,str(maker))
        proof="SELECT owner_guest_service_revenue_proof($1,$2,$3)"
        check(await conn.fetchval(proof,p,tid,day),700,"matched completed guest service")
        check(await conn.fetchval(proof,pb,tid,day),None,"foreign guest service rejected")
        check(await conn.fetchval(proof,p,tid,day-timedelta(days=1)),None,"wrong service date rejected")
        await conn.execute('UPDATE guest_folio_charges SET "amountKgs"=701 WHERE id=$1',fid)
        check(await conn.fetchval(proof,p,tid,day),None,"folio amount mismatch rejected")
        await conn.execute('UPDATE guest_folio_charges SET "amountKgs"=700 WHERE id=$1',fid)
        await conn.execute("""INSERT INTO owner_revenue_source_events
          (id,"propertyId","sourceType","sourceId","serviceDate",action,"faceValueKgs","sourceSnapshot",reason,"createdById")
          VALUES($1,$2,'OTHER_SERVICE',$3,$4,'APPROVE_SOURCE',700,'{}'::jsonb,'Synthetic completed service evidence',$5)""",
          sid,p,tid,day,maker)
        if refund_checks:
            # Canonical payment + audit evidence from a synthetic reservation.
            pay_id,refund_doc,refund_event=uuid.uuid4(),uuid.uuid4(),uuid.uuid4()
            reference="CI-REFUND-"+str(pay_id)
            content=b"%PDF-1.4 synthetic refund evidence"
            digest=hashlib.sha256(content).hexdigest()
            await conn.execute("""INSERT INTO payments
                (id,"reservationId","amountKgs",method,status,provider,"paidAt",metadata,"createdAt","updatedAt")
                VALUES($1,$2,100,'CASH','REFUNDED','MANAGER_MANUAL',now()-interval '1 day',
                 jsonb_build_object('manual_full_refund_evidence',
                  jsonb_build_object('reference',$3::text,'amount_kgs',100,
                    'recorded_by_staff_id',$4::text,'origin','EXTERNAL_ALREADY_COMPLETED',
                    'funds_sent_by_platform',false)),now(),now())""",pay_id,rid,reference,str(maker))
            await conn.execute("""INSERT INTO audit_logs
                (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES($1,$2,'STAFF',$3,'CONFIRM_MANUAL_FULL_REFUND','Payment',$4,'PMS_MANUAL_REFUND','SUCCESS',
                   jsonb_build_object('reservation_id',$5::text,'evidence_reference',$6::text,
                   'amount_kgs',100,'external_refund_previously_completed',true,'funds_sent_by_platform',false),now())""",
                uuid.uuid4(),p,str(maker),str(pay_id),str(rid),reference)
            await conn.execute("""INSERT INTO owner_revenue_evidence_documents
                (id,"propertyId","documentReference","documentDate","fileName","mediaType",sha256,content,"sizeBytes","uploadedById")
                VALUES($1,$2,$3,$4,'refund.pdf','application/pdf',$5,$6,$7,$8)""",
                refund_doc,p,reference,day,digest,content,len(content),maker)
            await conn.execute("""INSERT INTO owner_revenue_correction_events
                (id,"propertyId","approvalId",action,kind,component,"amountKgs","documentReference",
                 "documentDate","documentSha256","evidenceReference",reason,"sourceSnapshot","createdById","evidenceDocumentId")
                VALUES($1,$2,$3,'RECORD','REFUND','OTHER',100,$4,$5,$6,$4,
                       'Synthetic full refund cash evidence','{}'::jsonb,$7,$8)""",
                refund_event,p,sid,reference,day,digest,maker,refund_doc)
            refund_proof="SELECT owner_revenue_refund_payment_id($1,$2,$3)"
            check(await conn.fetchval(refund_proof,p,refund_event,reviewer),pay_id,"exact canonical full refund")
            check(await conn.fetchval(refund_proof,pb,refund_event,reviewer),None,"foreign refund excluded")
            check(await conn.fetchval(refund_proof,p,refund_event,maker),None,"refund maker cannot independently review")
        await conn.execute("""INSERT INTO owner_accounting_journal_proposals
          (id,"propertyId","sourceType","sourceId","accountingDate","policyVersion",reason,"payloadHash","createdById")
          SELECT $1,"propertyId","sourceType",$2,$3,"policyVersion",
                 'Synthetic other service proposal',$4,"createdById"
          FROM owner_accounting_journal_proposals WHERE id=$5 AND "propertyId"=$6""",
          qid,sid,day,hashlib.sha256(str(qid).encode()).hexdigest(),proposal,p)
        await conn.execute("""INSERT INTO owner_accounting_journal_proposal_lines
          ("proposalId","propertyId","lineNo","accountCode",side,"amountKgs")
          SELECT $1,"propertyId","lineNo",CASE WHEN "accountCode"='4200' THEN '4300' ELSE "accountCode" END,side,"amountKgs"
          FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$2 AND "propertyId"=$3""",qid,proposal,p)
        await conn.execute("""INSERT INTO owner_accounting_journal_decisions
          (id,"propertyId","proposalId",action,"actorId",reason)
          VALUES($1,$2,$3,'APPROVE',$4,'Independent other service decision')""",did,p,qid,reviewer)
        await conn.execute("""INSERT INTO owner_revenue_accounting_certifications
          (id,"propertyId","sourceEventId","evidenceDocumentId","reviewedById","grossAmountKgs","taxAmountKgs","netRevenueKgs","policyVersion",reason)
          SELECT $1,"propertyId",$2,"evidenceDocumentId","reviewedById","grossAmountKgs","taxAmountKgs","netRevenueKgs","policyVersion",
                 'Independent other service document review'
          FROM owner_revenue_accounting_certifications WHERE "propertyId"=$3 AND "sourceEventId"=$4""",uuid.uuid4(),sid,p,source)
        if refund_checks:
            check(await conn.fetchval("""SELECT "paymentId" FROM owner_revenue_refund_bindings
                WHERE "propertyId"=$1 AND "correctionEventId"=$2""",p,refund_event),pay_id,"refund uniquely bound")
        await race_post(conn,(sid,qid,did,reviewer))
        await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        check(await conn.fetchval("""SELECT l."amountKgs" FROM owner_accounting_posting_lines l
          JOIN owner_accounting_postings po ON po.id=l."postingId" AND po."propertyId"=l."propertyId"
          WHERE po."proposalId"=$1 AND l."accountCode"='4300' AND l.side='CREDIT'""",qid),650,"service net revenue to 4300")
        check(await conn.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),True,"guest service posting is active")
        if refund_checks:
            check(await conn.fetchval("""SELECT "reductionAmountKgs" FROM owner_revenue_accounting_certifications
                WHERE "propertyId"=$1 AND "sourceEventId"=$2""",p,sid),0,"cash refund never reduces earned revenue twice")
            return
        # Separate top-level transactions preserve the existing xmin seal.
        if mutation_checks:
            # Synthetic fixture only, within the outer rolled-back CI transaction.
            for statement, key in (
                ('UPDATE guest_folio_charges SET "amountKgs"=701 WHERE id=$1',fid),
                ("UPDATE guest_folio_charges SET status='VOID' WHERE id=$1",fid),
                ("UPDATE operational_tasks SET status='CANCELLED' WHERE id=$1",tid),
                ('UPDATE operational_tasks SET "serviceDate"="serviceDate"+1 WHERE id=$1',tid),
            ):
                try:
                    async with conn.transaction():
                        await conn.execute(statement,key)
                except asyncpg.CheckViolationError as exc:
                    check("OWNER_GUEST_SERVICE_ACTIVE_POSTING_REQUIRES_REVERSAL" in str(exc),True,
                          "posted source mutation rejected")
                else:
                    raise AssertionError("Posted guest service could be invalidated: "+statement)
            await conn.execute("UPDATE guest_folio_charges SET status='PAID' WHERE id=$1",fid)
            await conn.execute("""UPDATE operational_tasks SET "chargeStatus"='PAID' WHERE id=$1""",tid)
            check(await conn.fetchval(proof,p,tid,day),700,"normal payment preserves recognized service")
            return
        await conn.execute("SET CONSTRAINTS ALL DEFERRED")
        await clean_race_post(conn,(sid,qid,did,reviewer))
        await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        check(await conn.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),False,"exact guest service reversal")
        await conn.execute("UPDATE guest_folio_charges SET status='VOID' WHERE id=$1",fid)
        check(await conn.fetchval(proof,p,tid,day),None,"void permitted after exact accounting reversal")
    finally:
        await tx.rollback()
        await conn.close()
before_guest=checks
asyncio.run(verify_guest_service_ledger())
asyncio.run(verify_guest_service_ledger(mutation_checks=True))
print("MARINA_OWNER_GUEST_SERVICE_LEDGER_PASS",checks-before_guest)
before_refund=checks
asyncio.run(verify_guest_service_ledger(refund_checks=True))
print("MARINA_OWNER_CERTIFIED_REFUND_PASS",checks-before_refund)

# One invoice, multiple independently reviewed corrections, one posting.
# REFUND / PACKAGE_SPLIT are intentionally blocked from revenue recognition
# until their separate cash and delivery provenance is established.
def verify_combined_revenue_reductions():
    _,_,sid,_,doc_id=asyncio.run(seed())
    qid,post_id=uuid.uuid4(),uuid.uuid4()
    base="/api/v1/admin/finance/owner/accounting-journal"
    corr="/api/v1/admin/finance/owner/revenue-corrections"
    doc_bytes=b"%PDF-1.4\\n% Synthetic accounting source certification\\n%%EOF\\n"
    with TestClient(app,base_url="https://ledger-qa.invalid") as client:
        def sign_in(name):
            client.post("/api/v1/auth/logout")
            check(client.post("/api/v1/auth/login",json={"username":name,"password":PASSWORD}).status_code,200,"combined correction login")
        sign_in("owner")
        ids=[]
        def record(kind,amount,component="DINING"):
            eid=uuid.uuid4()
            response=client.post(corr,json={
                "id":str(eid),"approval_id":str(sid),"kind":kind,"component":component,
                "amount_kgs":amount,"document_reference":"CI-TAX-REVIEW-700",
                "document_date":date.today().isoformat(),"document_sha256":hashlib.sha256(doc_bytes).hexdigest(),
                "evidence_document_id":str(doc_id),"evidence_reference":"Synthetic invoice correction",
                "reason":"Independent review required for combined correction"})
            check(response.status_code,201,"record "+kind)
            return eid
        ids.extend([record("DISCOUNT","100"),record("CANCELLATION","50"),record("TAX_COMPONENT","40")])
        refund_id=record("REFUND","100")
        package_id=record("PACKAGE_SPLIT","200")
        cert={
            "id":str(uuid.uuid4()),"source_event_id":str(sid),"evidence_document_id":str(doc_id),
            "tax_amount_kgs":"40","reduction_amount_kgs":"150",
            "reduction_basis":"ADDITIONAL_TO_APPROVED_FACE",
            "correction_event_ids":[str(i) for i in ids],
            "policy_version":"CI-LEDGER-POLICY-1","reason":"Reviewed additional reductions not already in source face"}
        sign_in("accounting_reviewer")
        check(client.post(base+"/revenue-certifications",json={**cert,
            "correction_event_ids":[str(i) for i in [*ids,refund_id,package_id]]}).status_code,409,
            "refund and package cannot be silently included in revenue")
        sign_in("owner")
        for eid in (refund_id,package_id):
            check(client.post(corr+"/"+str(eid)+"/reverse",json={"id":str(uuid.uuid4()),
                "reason":"Remove unsupported synthetic evidence from fixture"}).status_code,201,"reverse unsupported evidence")
        proposal_body={
            "id":str(qid),"source_type":"REVENUE_SOURCE","source_id":str(sid),
            "accounting_date":date.today().isoformat(),"policy_version":"CI-LEDGER-POLICY-1",
            "reason":"Combined correction source posting after documentary review",
            "lines":[{"account_code":"1100","side":"DEBIT","amount_kgs":"550"},
                     {"account_code":"4200","side":"CREDIT","amount_kgs":"510"},
                     {"account_code":"2100","side":"CREDIT","amount_kgs":"40"}]}
        check(client.post(base+"/proposals",json=proposal_body).status_code,201,"combined reduced proposal")
        sign_in("accounting_reviewer")
        for change in ({"reduction_amount_kgs":"149"},{"correction_event_ids":[str(i) for i in ids[:-1]]},
                       {"reduction_basis":None},{"tax_amount_kgs":"39"}):
            check(client.post(base+"/revenue-certifications",json={**cert,**change}).status_code,409,
                  "reject mismatched correction certification")
        check(client.post(base+"/revenue-certifications",json=cert).status_code,201,"certify exact combined adjustments")
        check(client.post(base+"/revenue-certifications",json=cert).json()["already_processed"],True,"combined certification replay")
        decision_url=base+"/proposals/"+str(qid)+"/decisions"
        check(client.post(decision_url,json={"id":str(uuid.uuid4()),"action":"APPROVE",
              "reason":"Independent reduced revenue approval"}).status_code,201,"approve combined correction")
        check(client.post(base+"/proposals/"+str(qid)+"/post",json={"id":str(post_id),
              "reason":"Post exactly the reduced certified amount"}).status_code,201,"post reduced revenue")
        async def verify_lines():
            conn=await asyncpg.connect(parsed.geturl())
            try:
                lines=await conn.fetch("""SELECT "accountCode",side,"amountKgs"
                    FROM owner_accounting_posting_lines WHERE "postingId"=$1 AND "propertyId"=$2""",post_id,p)
                check(sorted((r["accountCode"],r["side"],int(r["amountKgs"])) for r in lines),
                      [("1100","DEBIT",550),("2100","CREDIT",40),("4200","CREDIT",510)],"exact net receivable and tax split")
            finally:
                await conn.close()
        asyncio.run(verify_lines())
        check(client.post(decision_url,json={"id":str(uuid.uuid4()),"action":"REVERSE",
              "reason":"Reverse synthetic combined correction posting"}).status_code,201,"approve reversal")
        check(client.post(base+"/postings/"+str(post_id)+"/reverse",json={"id":str(uuid.uuid4()),
              "reason":"Exact reversal of reduced revenue posting"}).status_code,201,"reverse combined posting")
        for eid in ids:
            check(client.post(corr+"/"+str(eid)+"/reverse",json={"id":str(uuid.uuid4()),
                  "reason":"Reverse evidence after synthetic ledger reversal"}).status_code,201,"reverse reviewed correction")
        check(client.post("/api/v1/admin/finance/owner/revenue-source-events/"+str(sid)+"/reverse",
              json={"id":str(uuid.uuid4()),"reason":"Close synthetic combined source fixture"}).status_code,201,"reverse source fixture")
before_combined=checks
verify_combined_revenue_reductions()
print("MARINA_OWNER_COMBINED_REDUCTIONS_PASS",checks-before_combined)
