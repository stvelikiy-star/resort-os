"""Two-hotel warehouse valuation test: actual PostgreSQL, no profit fabrication."""
import asyncio
import os
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse
from uuid import uuid4
import asyncpg
from fastapi.testclient import TestClient
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

dsn = os.environ.get("DATABASE_URL", "").split("?", 1)[0]
url = urlparse(dsn)
assert os.environ.get("MARINA_KITCHEN_COST_CI_CONFIRM") == "ISOLATED_KITCHEN_COST_ONLY"
assert os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "true"
assert os.environ.get("APP_ENV") == "staging"
assert url.hostname in ("127.0.0.1", "localhost") and url.path == "/marina_shared_browser_ci"

async def seed():
    db = await asyncpg.connect(dsn)
    try:
        items = {}
        async with db.transaction():
            assert await db.fetchval("SELECT count(*) FROM properties") == 2
            for code in ("HOTEL_A", "HOTEL_B"):
                pid = await db.fetchval("SELECT id FROM properties WHERE code=$1", code)
                assert pid is not None
                name = "Synthetic Cost " + code
                iid = uuid4()
                await db.execute(
                    'INSERT INTO kitchen_stock_items'
                    '(id,"propertyId",name,"nameKey",unit,"costPerUnitKgs","isSample")'
                    " VALUES($1,$2,$3,$4,'KG',12,false)",
                    iid, pid, name, name.casefold(),
                )
                items[code] = str(iid)
        return items
    finally:
        await db.close()

items = asyncio.run(seed())
checks = 0
with TestClient(app, base_url="https://synthetic-staging.invalid") as client:
    for letter in ("A", "B"):
        other = "B" if letter == "A" else "A"
        logged = client.post("/api/v1/auth/login", json={
            "username": "store_staff", "password": PASSWORD,
            "tenant_code": "tenant_" + letter.lower(),
            "property_code": "HOTEL_" + letter})
        assert logged.status_code == 200, logged.text
        receipt = {"movement_id": str(uuid4()), "stock_item_id": items["HOTEL_" + letter],
                   "quantity": "10", "notes": "Synthetic stock cost receipt"}
        response = client.post("/api/v1/kitchen/stock/receipts", json=receipt)
        assert response.status_code == 201, response.text
        checks += 1
        replay = client.post("/api/v1/kitchen/stock/receipts", json=receipt)
        assert replay.status_code == 201 and replay.json()["already_processed"] is True
        checks += 1
        foreign = client.post("/api/v1/kitchen/stock/losses", json={
            "movement_id": str(uuid4()), "stock_item_id": items["HOTEL_" + other],
            "kind": "SPOILAGE", "quantity": "1", "reason": "Synthetic cost"})
        assert foreign.status_code == 404, foreign.text
        checks += 1
        loss = {"movement_id": str(uuid4()), "stock_item_id": items["HOTEL_" + letter],
                "kind": "SPOILAGE", "quantity": "3", "reason": "Synthetic stock cost"}
        written = client.post("/api/v1/kitchen/stock/losses", json=loss)
        assert written.status_code == 201, written.text
        assert Decimal(written.json()["cost_kgs"]) == Decimal(36)
        checks += 2
        again = client.post("/api/v1/kitchen/stock/losses", json=loss)
        assert again.status_code == 201 and again.json()["already_processed"] is True
        checks += 1
        current = client.get("/api/v1/kitchen/stock").json()["items"]
        mine = next(item for item in current if item["id"] == items["HOTEL_" + letter])
        assert Decimal(mine["balance"]) == Decimal(7)
        assert Decimal(mine["inventory_value_kgs"]) == Decimal(84)
        checks += 2
        client.post("/api/v1/auth/logout")
        owner = client.post("/api/v1/auth/login", json={
            "username": "owner", "password": PASSWORD,
            "tenant_code": "tenant_" + letter.lower(),
            "property_code": "HOTEL_" + letter})
        assert owner.status_code == 200
        today = date.today().isoformat()
        report = client.get("/api/v1/admin/finance/owner/accrual-readiness", params={
            "from_date": today, "to_date": today})
        assert report.status_code == 200, report.text
        costs = report.json()["kitchen_cost_movements"]
        assert Decimal(costs["loss_cost_candidate_kgs"]) == Decimal(36), costs
        assert Decimal(costs["receipt_inventory_inflow_kgs"]) == Decimal(120), costs
        assert costs["costs_are_reconciled_to_revenue"] is False
        assert report.json()["recognition"]["recognized_profit_kgs"] is None
        checks += 4
        client.post("/api/v1/auth/logout")
print("MARINA_TWO_HOTEL_STOCK_COST_PROVENANCE_PASS", checks)
