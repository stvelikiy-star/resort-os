"""Real two-hotel PostgreSQL owner production-cost vs served-item candidate.

Run ONLY against disposable shared-staging CI PostgreSQL. This checks actual
foreign keys, grouping, session scope and that neither returned candidate is
booked as recognized profit.
"""
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

url = urlparse(os.environ.get("DATABASE_URL", "").split("?", 1)[0])
assert os.environ.get("MARINA_SERVED_COST_TRACE_CI_CONFIRM") == "ISOLATED_SERVED_COST_TRACE_ONLY"
assert os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "true"
assert os.environ.get("APP_ENV") == "staging"
assert url.hostname in ("localhost", "127.0.0.1")
assert url.path == "/marina_shared_browser_ci"
assert os.environ.get("MARINA_SHARED_BROWSER_CI_PASSWORD", "").startswith("synthetic-ci-only-")

async def seed():
    db = await asyncpg.connect(os.environ["DATABASE_URL"].split("?")[0])
    try:
        created = {}
        async with db.transaction():
            assert await db.fetchval("SELECT count(*) FROM properties") == 2
            for code in ("A", "B"):
                p = await db.fetchrow(
                    "SELECT id,timezone FROM properties WHERE code=$1", "HOTEL_" + code)
                assert p
                owner = await db.fetchval(
                    """SELECT id FROM staff_users WHERE "propertyId"=$1
                       AND role='OWNER'""", p["id"])
                assert owner
                service_date = await db.fetchval(
                    "SELECT (now() AT TIME ZONE $1)::date", p["timezone"])
                menu, target, stock, order = uuid4(), uuid4(), uuid4(), uuid4()
                await db.execute(
                    """INSERT INTO kitchen_menu_items
                       (id,"propertyId",code,category,"nameRu","nameKg","nameEn",
                        "priceKgs","isActive","isDraft")
                       VALUES($1,$2,$3,'MAIN','Synthetic dish','Synthetic dish',
                              'Synthetic dish',120,true,false)""",
                    menu, p["id"], "COST_TRACE_" + code,
                )
                await db.execute(
                    """INSERT INTO kitchen_production_targets
                       (id,"propertyId","menuItemId","serviceDate","mealType",
                        "plannedQuantity","preparedQuantity")
                       VALUES($1,$2,$3,$4,'LUNCH',10,10)""",
                    target, p["id"], menu, service_date,
                )
                await db.execute(
                    """INSERT INTO kitchen_stock_items
                       (id,"propertyId",name,"nameKey",unit,"costPerUnitKgs","isSample")
                       VALUES($1,$2,$3,$4,'KG',12,false)""",
                    stock, p["id"], "Synthetic cost trace " + code,
                    "synthetic cost trace " + code.lower(),
                )
                await db.execute(
                    """INSERT INTO kitchen_stock_movements
                       (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","createdById")
                       VALUES($1,$2,$3,'RECEIPT',10,12,$4)""",
                    uuid4(), p["id"], stock, owner,
                )
                await db.execute(
                    """INSERT INTO kitchen_stock_movements
                       (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs",
                        "productionTargetId","preparedFrom","preparedTo","createdById")
                       VALUES($1,$2,$3,'PRODUCTION',10,12,$4,0,10,$5)""",
                    uuid4(), p["id"], stock, target, owner,
                )
                await db.execute(
                    """INSERT INTO kitchen_stock_production_progress
                       ("propertyId","productionTargetId","deductedPortions")
                       VALUES($1,$2,10)""", p["id"], target,
                )
                await db.execute(
                    """INSERT INTO kitchen_orders
                       (id,"propertyId","orderNumber",status,source,"guestCount",
                        "mealType","totalKgs","openedById","completedAt")
                       VALUES($1,$2,$3,'SERVED','TABLE',2,'LUNCH',840,$4,now())""",
                    order, p["id"], "CI_COST_TRACE_" + code, owner,
                )
                await db.execute(
                    """INSERT INTO kitchen_order_items
                       (id,"orderId","menuItemId",quantity,"unitPriceKgs",
                        "lineTotalKgs",status)
                       VALUES($1,$2,$3,7,120,840,'SERVED')""",
                    uuid4(), order, menu,
                )
                created[code] = {"menu": str(menu), "date": service_date.isoformat()}
        return created
    finally:
        await db.close()

expected = asyncio.run(seed())
checks = 0
with TestClient(app, base_url="https://synthetic-staging.invalid") as client:
    for code in ("A", "B"):
        response = client.post("/api/v1/auth/login", json={
            "username": "owner", "password": PASSWORD,
            "tenant_code": "tenant_" + code.lower(),
            "property_code": "HOTEL_" + code})
        assert response.status_code == 200, response.text
        checks += 1
        day = expected[code]["date"]
        report = client.get(
            "/api/v1/admin/finance/owner/accrual-readiness",
            params={"from_date": day, "to_date": day})
        assert report.status_code == 200, report.text
        checks += 1
        trace = report.json()["served_kitchen_cost_trace"]
        assert trace["batch_to_order_link_verified"] is False
        assert trace["served_cost_is_accounting_cogs"] is False
        checks += 2
        rows = trace["items"]
        assert len(rows) == 1 and rows[0]["menu_item_id"] == expected[code]["menu"], rows
        checks += 1
        row = rows[0]
        assert row["prepared_portions"] == 10 and row["deducted_portions"] == 10
        assert row["served_portions"] == 7 and row["potentially_matched_portions"] == 7
        checks += 2
        assert Decimal(trace["totals"]["production_cost_kgs"]) == Decimal(120)
        assert Decimal(trace["totals"]["proportional_served_cost_candidate_kgs"]) == Decimal(84)
        assert Decimal(trace["totals"]["unallocated_production_cost_candidate_kgs"]) == Decimal(36)
        checks += 3
        recognized = report.json()["recognition"]
        assert recognized["recognized_profit_kgs"] is None
        assert "PRODUCTION_COST_TO_SERVED_ORDERS_NOT_ALLOCATED" in recognized["blockers"]
        checks += 2
        client.post("/api/v1/auth/logout")
print("MARINA_TWO_HOTEL_SERVED_COST_SOURCE_TRACE_PASS", checks)
