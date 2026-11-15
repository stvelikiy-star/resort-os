"""Isolated PostgreSQL/API E2E: supplier document -> procurement receipt links -> payable.

Never connects to production. Synthetic fixtures, explicit write opt-in.
This deliberately does NOT claim recognized COGS or profit.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import asyncpg
import httpx


def check(response, status, label):
    assert response.status_code == status, (label, response.status_code, response.text)
    return response.json()


async def login(client, username, password, role):
    response = await client.post("/api/v1/auth/login",
                                 json={"username": username, "password": password})
    check(response, 200, role + " login")
    client.headers["Cookie"] = "; ".join(f"{key}={value}"
                                         for key, value in response.cookies.items())
    profile = check(await client.get("/api/v1/auth/me"), 200, role + " profile")
    assert profile["role"] == role
    return profile


async def main():
    if os.getenv("ALLOW_SUPPLIER_DOCUMENT_TEST_WRITES") != "1":
        raise RuntimeError("Explicit isolated supplier-document test-write opt-in required")
    db_url = os.environ["DATABASE_URL"].split("?", 1)[0]
    if not ("@localhost:" in db_url or "@127.0.0.1:" in db_url):
        raise RuntimeError("Refusing non-local database")
    base = os.getenv("CORE_API_URL", "http://127.0.0.1:8000")
    if not base.startswith("http://127.0.0.1:"):
        raise RuntimeError("Refusing non-local Core API")
    conn = await asyncpg.connect(db_url)
    item_id = doc_id = request_id = None
    receipt_ids = []
    try:
        async with httpx.AsyncClient(base_url=base, timeout=30) as owner, \
                   httpx.AsyncClient(base_url=base, timeout=30) as store:
            owner_me = await login(owner, os.environ["BOOTSTRAP_OWNER_USERNAME"],
                                   os.environ["BOOTSTRAP_OWNER_PASSWORD"], "OWNER")
            await login(store, os.environ["PROC_STORE_USERNAME"],
                        os.environ["PROC_STORE_PASSWORD"], "STORE_STAFF")
            pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1",
                                      owner_me["property_code"])
            assert pid is not None
            payment_before = await conn.fetchval("SELECT COUNT(*) FROM payments")
            expenses_before = await conn.fetchval(
                'SELECT COUNT(*) FROM owner_expenses WHERE "propertyId"=$1', pid)
            token = uuid.uuid4().hex[:12]
            item_id = check(await owner.post("/api/v1/kitchen/stock/items", json={
                "name": "supplier-contract-" + token, "unit": "KG",
                "cost_per_unit_kgs": "100", "is_sample": False,
            }), 201, "new stock item")["id"]
            doc_id = str(uuid.uuid4())
            line_id = str(uuid.uuid4())
            today = await conn.fetchval(
                'SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1', pid)
            body = {
                "id": doc_id, "supplier_name": "Supplier test " + token,
                "document_reference": "INV-" + token,
                "document_date": today.isoformat(),
                "lines": [{"id": line_id, "stock_item_id": item_id,
                           "quantity": "5", "unit_cost_kgs": "123.4567"}],
            }
            denied = await store.post(
                "/api/v1/admin/finance/owner/supplier-documents", json=body)
            check(denied, 403, "STORE cannot post OWNER financial document")
            created = check(await owner.post(
                "/api/v1/admin/finance/owner/supplier-documents", json=body),
                201, "create document")
            assert created["amount_kgs"] == "617.2835"
            assert created["recognized_profit"] is False
            same = check(await owner.post(
                "/api/v1/admin/finance/owner/supplier-documents", json=body),
                201, "identical document retry")
            assert same["already_processed"] is True
            check(await owner.post("/api/v1/admin/finance/owner/supplier-documents",
                                   json={**body, "lines": [
                                       {**body["lines"][0], "unit_cost_kgs": "120"}]}),
                  409, "modified document must conflict")
            request_id = str(uuid.uuid4())
            check(await owner.post("/api/v1/kitchen/procurement/requests", json={
                "request_id": request_id, "stock_item_id": item_id,
                "quantity": "5", "service_date": today.isoformat()
            }), 201, "procurement request")
            check(await owner.post(
                f"/api/v1/kitchen/procurement/requests/{request_id}/approve"),
                200, "approve")
            for qty in ("2", "3"):
                rid = str(uuid.uuid4())
                receipt_ids.append(rid)
                accepted = check(await store.post(
                    f"/api/v1/kitchen/procurement/requests/{request_id}/receive",
                    json={"receipt_id": rid, "quantity": qty}), 201, "receive")
                assert accepted["payment_created"] is False
                binding = {"receipt_id": rid, "document_line_id": line_id}
                links = await asyncio.gather(*[
                    owner.post(f"/api/v1/admin/finance/owner/supplier-documents/{doc_id}/receipt-links",
                               json=binding) for _ in range(8)])
                assert all(r.status_code == 201 for r in links), [r.text for r in links]
                assert sum(not r.json()["already_processed"] for r in links) == 1
            allocated = await conn.fetchval(
                'SELECT COALESCE(SUM(quantity),0) FROM kitchen_supplier_receipt_links '
                'WHERE "propertyId"=$1 AND "documentLineId"=$2', pid, uuid.UUID(line_id))
            assert allocated == Decimal("5")
            assert await conn.fetchval(
                'SELECT COUNT(*) FROM kitchen_supplier_receipt_links '
                'WHERE "propertyId"=$1 AND "documentLineId"=$2',
                pid, uuid.UUID(line_id)) == 2
            check(await owner.post(
                f"/api/v1/admin/finance/owner/supplier-documents/{doc_id}/receipt-links",
                json={"receipt_id": receipt_ids[0],
                      "document_line_id": str(uuid.uuid4())}), 404, "unknown line")
            check(await store.get(
                "/api/v1/admin/finance/owner/supplier-documents"),
                403, "STORE denied OWNER invoice totals")
            invoice = check(await owner.get(
                "/api/v1/admin/finance/owner/supplier-documents"),
                200, "list payables")
            row = next(x for x in invoice["items"] if x["id"] == doc_id)
            assert Decimal(row["outstanding_kgs"]) == Decimal("617.2835")
            settle_id = str(uuid.uuid4())
            settle = {"id": settle_id, "amount_kgs": "200",
                      "paid_on": today.isoformat(), "method": "BANK_TRANSFER",
                      "reference": "test-" + token}
            path = (f"/api/v1/admin/finance/owner/supplier-documents/"
                    f"{doc_id}/settlements")
            requests = await asyncio.gather(*[
                owner.post(path, json=settle) for _ in range(8)])
            assert all(r.status_code == 201 for r in requests), [r.text for r in requests]
            assert sum(not r.json()["already_processed"] for r in requests) == 1
            check(await owner.post(path, json={**settle, "amount_kgs": "201"}),
                  409, "changed settlement UUID")
            check(await owner.post(path, json={**settle, "id": str(uuid.uuid4()),
                                               "amount_kgs": "418"}),
                  409, "cannot overpay invoice")
            check(await owner.post(path, json={**settle, "id": str(uuid.uuid4()),
                                               "amount_kgs": "417.2835"}),
                  201, "settle remainder")
            final = check(await owner.get(
                "/api/v1/admin/finance/owner/supplier-documents"),
                200, "final totals")
            row = next(x for x in final["items"] if x["id"] == doc_id)
            assert Decimal(row["outstanding_kgs"]) == 0
            assert Decimal(row["settled_kgs"]) == Decimal("617.2835")
            assert await conn.fetchval("SELECT COUNT(*) FROM payments") == payment_before
            assert await conn.fetchval(
                'SELECT COUNT(*) FROM owner_expenses WHERE "propertyId"=$1',
                pid) == expenses_before
            assert await conn.fetchval(
                'SELECT COUNT(*) FROM kitchen_stock_movements '
                'WHERE id=ANY($1::uuid[])',
                [uuid.UUID(x) for x in receipt_ids]) == 2
            print("SUPPLIER_DOCUMENT_POSTGRES_E2E_PASS: invoice, two receipts, "
                  "8 concurrent retries, settlements, owner-only, no customer Payment")
    finally:
        if doc_id or request_id or item_id:
            async with conn.transaction():
                if doc_id:
                    await conn.execute(
                        'DELETE FROM kitchen_supplier_receipt_links '
                        'WHERE "documentLineId" IN '
                        '(SELECT id FROM kitchen_supplier_document_lines WHERE "documentId"=$1)',
                        uuid.UUID(doc_id))
                    await conn.execute(
                        'DELETE FROM kitchen_supplier_settlements WHERE "documentId"=$1',
                        uuid.UUID(doc_id))
                    await conn.execute(
                        'DELETE FROM kitchen_supplier_document_lines WHERE "documentId"=$1',
                        uuid.UUID(doc_id))
                    await conn.execute(
                        "DELETE FROM kitchen_supplier_documents WHERE id=$1",
                        uuid.UUID(doc_id))
                for rid in receipt_ids:
                    await conn.execute(
                        "DELETE FROM kitchen_procurement_receipts WHERE id=$1",
                        uuid.UUID(rid))
                    await conn.execute(
                        "DELETE FROM kitchen_stock_movements WHERE id=$1",
                        uuid.UUID(rid))
                if request_id:
                    await conn.execute(
                        "DELETE FROM kitchen_procurement_requests WHERE id=$1",
                        uuid.UUID(request_id))
                if item_id:
                    await conn.execute(
                        "DELETE FROM kitchen_stock_items WHERE id=$1",
                        uuid.UUID(item_id))
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
