"""Disposable-only PostgreSQL/API acceptance of immutable, unposted OWNER proposals.

Runs after verify_owner_revenue_source_journal_e2e.py has seeded synthetic
verified revenue evidence. NEVER run against a live hotel.
"""
import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal

import asyncpg
import httpx


def expect(response, code, label):
    assert response.status_code == code, (label, response.status_code, response.text)
    return response.json()


async def main():
    if os.getenv("ALLOW_REVENUE_JOURNAL_SYNTHETIC_CI") != "1":
        raise RuntimeError("Explicit disposable CI opt-in required")
    database = os.environ["DATABASE_URL"].split("?", 1)[0]
    api = os.getenv("CORE_API_URL", "http://127.0.0.1:8000")
    if not any(part in database for part in ("@localhost:", "@127.0.0.1:")):
        raise RuntimeError("Refusing external PostgreSQL")
    if not api.startswith("http://127.0.0.1:"):
        raise RuntimeError("Refusing non-local API")
    db = await asyncpg.connect(database)
    try:
        async with httpx.AsyncClient(base_url=api, timeout=40) as owner, \
                   httpx.AsyncClient(base_url=api, timeout=40) as cook:
            expect(await owner.post("/api/v1/auth/login", json={
                "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
                "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"]
            }), 200, "owner login")
            expect(await cook.post("/api/v1/auth/login", json={
                "username": os.environ["KITCHEN_MENU_DINING_USERNAME"],
                "password": os.environ["KITCHEN_MENU_DINING_PASSWORD"]
            }), 200, "cook login")
            me = expect(await owner.get("/api/v1/auth/me"), 200, "owner identity")
            pid = await db.fetchval("SELECT id FROM properties WHERE code=$1", me["property_code"])
            source = await db.fetchrow(
                """SELECT e.id FROM owner_revenue_source_events e
                   WHERE e."propertyId"=$1 AND e.action='APPROVE_SOURCE'
                     AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events rev
                        WHERE rev."propertyId"=e."propertyId"
                          AND rev."reversesId"=e.id)
                   ORDER BY e."createdAt" DESC LIMIT 1""", pid)
            assert source, "Requires verified synthetic active source from preceding E2E"
            before_payments = await db.fetchval("SELECT COUNT(*) FROM payments")
            url = "/api/v1/admin/finance/owner/accounting-journal/proposals"
            operation = uuid.uuid4()
            today = date.today().isoformat()
            body = {
                "id": str(operation), "source_type": "REVENUE_SOURCE",
                "source_id": str(source["id"]), "accounting_date": today,
                "policy_version": "UNAPPROVED-CI-v1",
                "reason": "Synthetic verification proposal, no recognition",
                "lines": [
                    {"account_code": "1000", "side": "DEBIT", "amount_kgs": "333.3333"},
                    {"account_code": "4000", "side": "CREDIT", "amount_kgs": "333.3333"}
                ]
            }
            expect(await cook.post(url, json=body), 403, "cook cannot propose")
            expect(await cook.get(url, params={"from_date": today, "to_date": today}),
                   403, "cook cannot read")
            expect(await owner.post(url, json={
                **body, "id": str(uuid.uuid4()),
                "source_id": str(uuid.uuid4())
            }), 409, "unknown evidence blocked")
            reversed_source = await db.fetchval(
                """SELECT e.id FROM owner_revenue_source_events e
                   WHERE e."propertyId"=$1 AND e.action='APPROVE_SOURCE'
                     AND EXISTS(SELECT 1 FROM owner_revenue_source_events rev
                       WHERE rev."propertyId"=e."propertyId"
                         AND rev."reversesId"=e.id)
                   LIMIT 1""", pid)
            assert reversed_source, "Synthetic source E2E must include a reversal"
            expect(await owner.post(url, json={**body,
                "id": str(uuid.uuid4()), "source_id": str(reversed_source)}),
                409, "reversed source cannot be proposed")
            unbalanced = {**body, "lines": [body["lines"][0], {
                "account_code": "4000", "side": "CREDIT", "amount_kgs": "333.3332"
            }]}
            expect(await owner.post(url, json=unbalanced), 422,
                   "unbalanced API write rejected")
            answers = await asyncio.gather(*[owner.post(url, json=body) for _ in range(8)])
            assert all(r.status_code == 201 for r in answers), [
                (r.status_code, r.text) for r in answers]
            posted = [r.json() for r in answers]
            assert sum(not p["already_processed"] for p in posted) == 1
            assert all(p["status"] == "PENDING_ACCOUNTANT_APPROVAL" for p in posted)
            assert all(p["recognized_profit_kgs"] is None for p in posted)
            assert all(p["accounting_posted"] is False for p in posted)
            expect(await owner.post(url, json={**body,
                "reason": "Changed reason for the same operation"}), 409,
                "changed same ID 409")
            expect(await owner.post(url, json={**body, "id": str(uuid.uuid4())}),
                   409, "duplicate source 409")
            found = expect(await owner.get(url, params={
                "from_date": today, "to_date": today
            }), 200, "owner listing")
            assert sum(row["id"] == str(operation) for row in found["items"]) == 1
            assert found["recognized_profit_kgs"] is None
            stored = await db.fetchrow(
                """SELECT h."propertyId",h.status,COUNT(l."lineNo") AS n,
                          SUM(l."amountKgs") FILTER(WHERE l.side='DEBIT') AS debit,
                          SUM(l."amountKgs") FILTER(WHERE l.side='CREDIT') AS credit
                     FROM owner_accounting_journal_proposals h
                     JOIN owner_accounting_journal_proposal_lines l
                       ON l."proposalId"=h.id AND l."propertyId"=h."propertyId"
                    WHERE h.id=$1 GROUP BY h."propertyId",h.status""", operation)
            assert stored and stored["propertyId"] == pid
            assert stored["n"] == 2 and stored["debit"] == stored["credit"]
            assert Decimal(stored["debit"]) == Decimal("333.3333")

            for sql, args, label in [
                ('UPDATE owner_accounting_journal_proposals SET reason=$1 WHERE id=$2',
                 ("Overwritten", operation), "header rewrite"),
                ('DELETE FROM owner_accounting_journal_proposal_lines WHERE "proposalId"=$1',
                 (operation,), "line deletion"),
                ('DELETE FROM owner_accounting_journal_proposals WHERE id=$1',
                 (operation,), "header deletion"),
                ('UPDATE owner_accounting_journal_proposal_lines SET "amountKgs"=$1 WHERE "proposalId"=$2',
                 (Decimal("1"), operation), "line rewrite"),
                ('INSERT INTO owner_accounting_journal_proposal_lines ("proposalId","propertyId","lineNo","accountCode","side","amountKgs") VALUES($1,$2,3,$3,$4,$5)',
                 (operation, pid, "1000", "DEBIT", Decimal("1")), "late line append"),
            ]:
                try:
                    await db.execute(sql, *args)
                except asyncpg.PostgresError:
                    pass
                else:
                    raise AssertionError(label + " must fail")
            owner_staff = await db.fetchval(
                'SELECT id FROM staff_users WHERE "propertyId"=$1 LIMIT 1', pid)
            assert owner_staff
            for missing_lines in (True, False):
                other_id = uuid.uuid4()
                try:
                    async with db.transaction():
                        await db.execute(
                            """INSERT INTO owner_accounting_journal_proposals
                               (id,"propertyId","sourceType","sourceId",
                                "accountingDate","policyVersion",reason,
                                "payloadHash","createdById")
                               VALUES($1,$2,'REVENUE_SOURCE',$3,$4,$5,$6,$7,$8)""",
                            other_id, pid, uuid.uuid4(), date.today(),
                            "UNAPPROVED-CI-v1", "Deliberately invalid SQL proposal",
                            "a"*64, owner_staff)
                        if not missing_lines:
                            for index, side, amount in [
                                (1, "DEBIT", Decimal("20")),
                                (2, "CREDIT", Decimal("19"))
                            ]:
                                await db.execute(
                                    """INSERT INTO owner_accounting_journal_proposal_lines
                                       ("proposalId","propertyId","lineNo",
                                        "accountCode",side,"amountKgs")
                                       VALUES($1,$2,$3,$4,$5,$6)""",
                                    other_id, pid, index, "1000", side, amount)
                except asyncpg.CheckViolationError:
                    pass
                else:
                    raise AssertionError("Direct SQL empty/unbalanced proposal committed")
                assert await db.fetchval(
                    "SELECT COUNT(*) FROM owner_accounting_journal_proposals WHERE id=$1",
                    other_id) == 0, "Invalid SQL must roll back atomically"
            after_payments = await db.fetchval("SELECT COUNT(*) FROM payments")
            assert after_payments == before_payments
            print("OWNER_ACCOUNTING_JOURNAL_PG_E2E_PASS: roles, immutable SQL, balance,"
                  " 8-way replay, 409, tenant source, no Payment or posted P&L")


if __name__ == "__main__":
    asyncio.run(main())
