"""Isolated PostgreSQL E2E: OWNER expenses and manual settlements, never real payments.

Run only with explicit CI opt-in, localhost DB and localhost API.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import asyncpg
import httpx

def checked(response,status,label):
    assert response.status_code==status,(label,response.status_code,response.text)
    return response.json()

async def login(client,user,password,role):
    response=checked(await client.post("/api/v1/auth/login",json={
        "username":user,"password":password}),200,role+" login")
    client.headers["Cookie"]="; ".join(f"{k}={v}" for k,v in (
        await client.post("/api/v1/auth/login",json={
            "username":user,"password":password})
    ).cookies.items())
    me=checked(await client.get("/api/v1/auth/me"),200,role+" profile")
    assert me["role"]==role
    return me

async def main():
    if os.environ.get("ALLOW_OWNER_EXPENSE_TEST_WRITES")!="1":
        raise RuntimeError("Requires explicit disposable PostgreSQL opt-in")
    url=os.environ["DATABASE_URL"].split("?",1)[0]
    if not ("@localhost:" in url or "@127.0.0.1:" in url):
        raise RuntimeError("Refusing non-local DB")
    base=os.environ.get("CORE_API_URL","http://127.0.0.1:8000")
    if not base.startswith("http://127.0.0.1:"):
        raise RuntimeError("Refusing remote API")
    db=await asyncpg.connect(url)
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner, \
                   httpx.AsyncClient(base_url=base,timeout=30) as cook:
            me=await login(owner,os.environ["BOOTSTRAP_OWNER_USERNAME"],
                           os.environ["BOOTSTRAP_OWNER_PASSWORD"],"OWNER")
            cook_me=await login(cook,os.environ["KITCHEN_MENU_DINING_USERNAME"],
                        os.environ["KITCHEN_MENU_DINING_PASSWORD"],"COOK")
            # A legacy custom FINANCE grant used to bypass OWNER-only role
            # dependencies. Exercise actual sessions + PostgreSQL permissions.
            cook_id=uuid.UUID(cook_me["id"])
            previous_permissions=await db.fetchval(
                'SELECT "modulePermissions" FROM staff_users WHERE id=$1',cook_id)
            try:
                await db.execute('UPDATE staff_users SET "modulePermissions"=$1::jsonb WHERE id=$2',
                                 '["FINANCE","DINING"]',cook_id)
                await login(cook,os.environ["KITCHEN_MENU_DINING_USERNAME"],
                            os.environ["KITCHEN_MENU_DINING_PASSWORD"],"COOK")
                owner_base="/api/v1/admin/finance/owner"
                for suffix in ("/expenses","/recorded-cash-movements","/kitchen-operations"):
                    checked(await cook.get(owner_base+suffix,params={
                        "from_date":"2026-11-15","to_date":"2026-11-15"}),403,
                        "custom FINANCE must not promote COOK to OWNER")
                checked(await cook.post(owner_base+"/expenses",json={
                    "id":str(uuid.uuid4()),"expense_date":"2026-11-15",
                    "category":"OTHER","title":"Denied custom grant","amount_kgs":1}),
                    403,"custom FINANCE cannot create OWNER expense")
            finally:
                await db.execute('UPDATE staff_users SET "modulePermissions"=$1::jsonb WHERE id=$2',
                                 previous_permissions,cook_id)
                await login(cook,os.environ["KITCHEN_MENU_DINING_USERNAME"],
                            os.environ["KITCHEN_MENU_DINING_PASSWORD"],"COOK")
            pid=await db.fetchval('SELECT id FROM properties WHERE code=$1',me["property_code"])
            assert pid is not None
            today=await db.fetchval(
                "SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1",pid)
            date_str=today.isoformat()
            basepath="/api/v1/admin/finance/owner/expenses"
            payment_count=await db.fetchval("SELECT COUNT(*) FROM payments")
            initial=checked(await owner.get(basepath,params={
                "from_date":date_str,"to_date":date_str}),200,"initial ledger")
            summary_base=checked(await owner.get("/api/v1/admin/finance/summary",params={
                "from_date":date_str,"to_date":date_str}),200,"financial overview")
            assert "owner_expense_snapshot" in summary_base
            assert "owner_accrual_readiness_snapshot" in summary_base
            assert summary_base["owner_accrual_readiness_snapshot"]["recognition"]["recognized_profit_kgs"] is None
            init=summary_base["owner_expense_snapshot"]
            accrual_url="/api/v1/admin/finance/owner/accrual-readiness"
            accrual_range={"from_date":date_str,"to_date":date_str}
            checked(await cook.get(accrual_url,params=accrual_range),403,
                    "COOK cannot access accrual readiness")
            before_accrual=checked(await owner.get(accrual_url,params=accrual_range),
                                   200,"OWNER accrual baseline")
            initial_posted=Decimal(before_accrual["posted_owner_obligations"]["posted_total_kgs"])
            assert before_accrual["recognition"]["recognized_revenue_kgs"] is None
            assert before_accrual["recognition"]["recognized_expenses_kgs"] is None
            assert before_accrual["recognition"]["recognized_profit_kgs"] is None
            assert before_accrual["recognition"]["completeness_verified"] is False
            assert before_accrual["recognition"]["source_candidates_are_recognized"] is False
            cash_url="/api/v1/admin/finance/owner/recorded-cash-movements"
            before_cash=checked(await owner.get(cash_url,params={
                "from_date":date_str,"to_date":date_str}),200,"cash movement baseline")
            assert before_cash["truth"]["recognized_profit_kgs"] is None
            assert before_cash["truth"]["completeness_verified"] is False
            checked(await cook.get(cash_url,params={"from_date":date_str,
                "to_date":date_str}),403,"cook denied owner cash movement reconciliation")
            checked(await cook.get(basepath,params={
                "from_date":date_str,"to_date":date_str}),403,"cook read denied")
            expense_id=str(uuid.uuid4())
            amount=1000
            payload={"id":expense_id,"expense_date":date_str,"category":"UTILITIES",
                "title":" E2E   electricity ", "amount_kgs":amount,
                "supplier_name":"E2E Power", "document_reference":"TEST-"+expense_id,
                "notes":"Synthetic CI obligation"}
            checked(await cook.post(basepath,json=payload),403,"cook write denied")
            created=checked(await owner.post(basepath,json=payload),201,"expense posting")
            assert created=={"id":expense_id,"status":"POSTED",
                            "already_processed":False,"payment_created":False}
            replay=checked(await owner.post(basepath,json=payload),201,"expense replay")
            assert replay["already_processed"] is True
            checked(await owner.post(basepath,json={**payload,"amount_kgs":999}),
                    409,"conflicting expense ID")
            row=checked(await owner.get(basepath,params={
                "from_date":date_str,"to_date":date_str}),200,"posted expense")
            current=next(x for x in row["items"] if x["id"]==expense_id)
            assert current["amount_kgs"]==1000 and current["outstanding_kgs"]==1000
            assert row["totals"]["posted_expenses_kgs"]-initial["totals"]["posted_expenses_kgs"]==1000
            after_post_accrual=checked(await owner.get(accrual_url,params=accrual_range),
                                       200,"OWNER after obligation")
            assert Decimal(after_post_accrual["posted_owner_obligations"]["posted_total_kgs"])-initial_posted==Decimal("1000")
            assert after_post_accrual["recognition"]["recognized_profit_kgs"] is None
            assert await db.fetchval("SELECT count(*) FROM payments")==payment_count
            settle_id=str(uuid.uuid4())
            settlement={"id":settle_id,"amount_kgs":300,"paid_on":date_str,
                        "method":"BANK_TRANSFER","reference":"Manual bank transfer E2E"}
            checked(await cook.post(f"{basepath}/{expense_id}/settlements",json=settlement),
                    403,"cook settlement denied")
            paid=checked(await owner.post(f"{basepath}/{expense_id}/settlements",
                                json=settlement),201,"manual partial settlement")
            assert paid["source"]=="MANUAL_EXPENSE_SETTLEMENT_FACT"
            assert paid["payment_created"] is False
            retry=checked(await owner.post(f"{basepath}/{expense_id}/settlements",
                                  json=settlement),201,"settlement replay")
            assert retry["already_processed"] is True
            checked(await owner.post(f"{basepath}/{expense_id}/settlements",
                                  json={**settlement,"amount_kgs":301}),409,"conflicting receipt UUID")
            checked(await owner.post(f"{basepath}/{expense_id}/settlements",json={
                **settlement,"id":str(uuid.uuid4()),"amount_kgs":701}),
                    409,"over settlement blocked")
            checked(await owner.post(f"{basepath}/{expense_id}/void",json={
                "reason":"Cannot void paid expense"}),409,"paid expense cannot be voided")
            final=checked(await owner.get(basepath,params={
                "from_date":date_str,"to_date":date_str}),200,"final ledger")
            item=next(x for x in final["items"] if x["id"]==expense_id)
            assert item["settled_kgs"]==300 and item["outstanding_kgs"]==700
            after_settlement_accrual=checked(await owner.get(accrual_url,params=accrual_range),
                                             200,"OWNER after settlement")
            assert after_settlement_accrual["posted_owner_obligations"]==after_post_accrual["posted_owner_obligations"], "settlement must not change posted cost"
            assert after_settlement_accrual["recognition"]["recognized_profit_kgs"] is None
            financial=checked(await owner.get("/api/v1/admin/finance/summary",params={
                "from_date":date_str,"to_date":date_str}),200,"finance integration")
            snap=financial["owner_expense_snapshot"]
            assert snap["period_posted_obligations_kgs"]-init["period_posted_obligations_kgs"]==1000
            assert snap["period_manually_recorded_settlements_kgs"]-init["period_manually_recorded_settlements_kgs"]==300
            assert snap["all_time_outstanding_obligations_kgs"]-init["all_time_outstanding_obligations_kgs"]==700
            assert financial["owner_accrual_readiness_snapshot"]["posted_owner_obligations"]==after_settlement_accrual["posted_owner_obligations"]
            assert financial["owner_accrual_readiness_snapshot"]["recognition"]["recognized_profit_kgs"] is None
            assert financial["scope"]["accounting_report"] is False
            assert await db.fetchval("SELECT count(*) FROM payments")==payment_count
            after_cash=checked(await owner.get(cash_url,params={
                "from_date":date_str,"to_date":date_str}),200,"cash movements after settlement")
            assert (after_cash["owner_expense_manual_settlements_kgs"]-
                    before_cash["owner_expense_manual_settlements_kgs"])==300
            assert (after_cash["owner_expenses_posted_for_period_kgs"]-
                    before_cash["owner_expenses_posted_for_period_kgs"])==1000
            assert (after_cash["observed_recorded_difference_kgs"]-
                    before_cash["observed_recorded_difference_kgs"])==-300
            assert (after_cash["customer_payments_received_kgs"]==
                    before_cash["customer_payments_received_kgs"])
            assert after_cash["truth"]["recognized_profit_kgs"] is None
            assert after_cash["truth"]["verified_bank_balance_kgs"] is None
            assert after_cash["truth"]["refunds_reconciled"] is False
            assert after_cash["truth"]["payment_created"] is False
            void_id=str(uuid.uuid4())
            voided=checked(await owner.post(basepath,json={**payload,"id":void_id,
                "title":"Cancelled E2E supply expense"}),201,"create cancelable item")
            assert voided["status"]=="POSTED"
            cancelled=checked(await owner.post(f"{basepath}/{void_id}/void",json={
                "reason":"Duplicated purchase request, never paid"}),200,"void unpaid")
            assert cancelled["status"]=="VOID"
            again=checked(await owner.post(f"{basepath}/{void_id}/void",json={
                "reason":"Duplicated purchase request, never paid"}),200,"void replay")
            assert again["already_processed"] is True
            checked(await owner.post(f"{basepath}/{void_id}/settlements",json={
                **settlement,"id":str(uuid.uuid4())}),409,"voided cannot settle")
            checked(await owner.get(basepath,params={
                "from_date":"2026-11-16","to_date":"2026-11-15"}),422,"invalid date range")
            print("OWNER CASH RECONCILIATION POSTGRES PASS: observed customer receipt unchanged, manual payout +300, difference -300, no profit or verified balance")
            print("OWNER EXPENSES REAL POSTGRES: PASS obligation 1000 -> manual 300 -> 700 payable, no customer Payment, OWNER gate, UUID replay, conflict, overpay and VOID")
    finally:
        await db.close()

if __name__=="__main__":
    asyncio.run(main())
