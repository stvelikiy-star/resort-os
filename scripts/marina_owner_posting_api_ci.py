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
async def verify_guest_service_ledger():
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
        await race_post(conn,(sid,qid,did,reviewer))
        await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        check(await conn.fetchval("""SELECT l."amountKgs" FROM owner_accounting_posting_lines l
          JOIN owner_accounting_postings po ON po.id=l."postingId" AND po."propertyId"=l."propertyId"
          WHERE po."proposalId"=$1 AND l."accountCode"='4300' AND l.side='CREDIT'""",qid),650,"service net revenue to 4300")
        check(await conn.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),True,"guest service posting is active")
        await conn.execute("SET CONSTRAINTS ALL DEFERRED")
        await clean_race_post(conn,(sid,qid,did,reviewer))
        await conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
        check(await conn.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",p,sid),False,"exact guest service reversal")
    finally:
        await tx.rollback()
        await conn.close()
before_guest=checks
asyncio.run(verify_guest_service_ledger())
print("MARINA_OWNER_GUEST_SERVICE_LEDGER_PASS",checks-before_guest)
