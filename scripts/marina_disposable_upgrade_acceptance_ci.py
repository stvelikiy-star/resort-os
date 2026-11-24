#!/usr/bin/env python3
"""MARINA upgrade acceptance on disposable old->new PostgreSQL 16 copies ONLY."""
from __future__ import annotations
import asyncio
import json
import os
import sys
from pathlib import Path
import asyncpg
import httpx

EVIDENCE = Path("migration-evidence")
EVIDENCE.mkdir(exist_ok=True)


async def database_snapshot(url: str):
    conn = await asyncpg.connect(url)
    try:
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        result = {}
        for (name,) in tables:
            if name == "_prisma_migrations":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            keys = await conn.fetchval("""
                SELECT array_agg(a.attname ORDER BY k.ord)
                FROM pg_index i
                CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(num,ord)
                JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num
                WHERE i.indrelid=$1::text::regclass AND i.indisprimary
            """, quoted)
            rows = await conn.fetch(f"SELECT to_jsonb(t)::text AS payload FROM {quoted} t")
            assert keys or not rows, f"No primary key in {name}"
            result[name] = {}
            for (raw,) in rows:
                item = json.loads(raw)
                key = "|".join(str(item[k]) for k in keys)
                assert key not in result[name], f"Duplicate PK {name} {key}"
                result[name][key] = item
        result["_meta"] = {
            "migrations": await conn.fetchval('SELECT count(*) FROM _prisma_migrations WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL'),
            "property_count": await conn.fetchval("SELECT count(*) FROM properties"),
            "staff_count": await conn.fetchval("SELECT count(*) FROM staff_users"),
            "reservation_count": await conn.fetchval("SELECT count(*) FROM reservations"),
            "payment_kgs": await conn.fetchval('SELECT coalesce(sum("amountKgs"),0) FROM payments'),
            "folio_kgs": await conn.fetchval('SELECT coalesce(sum("amountKgs"),0) FROM guest_folio_charges'),
            "orders_kgs": await conn.fetchval('SELECT coalesce(sum("totalKgs"),0) FROM kitchen_orders'),
        }
        return result
    finally:
        await conn.close()


async def snapshot_stage(label):
    assert label in ("old", "clone", "new", "rollback")
    urls = {
        "old": os.environ["MARINA_LEGACY_OLD_DB"],
        "clone": os.environ["MARINA_LEGACY_NEW_DB"],
        "new": os.environ["MARINA_LEGACY_NEW_DB"],
        "rollback": os.environ["MARINA_LEGACY_ROLLBACK_DB"],
    }
    snap = await database_snapshot(urls[label])
    (EVIDENCE / f"{label}.json").write_text(json.dumps(snap, sort_keys=True, ensure_ascii=False, indent=2))
    print(label.upper(), snap["_meta"])


def verify_preservation():
    load = lambda name: json.loads((EVIDENCE / f"{name}.json").read_text())
    before, clone, after, rollback = map(load, ("old", "clone", "new", "rollback"))
    assert before == clone, "Dump restore not byte-equivalent at row/field level"
    assert before == rollback, "Independent rollback restore differs"
    assert before["_meta"]["migrations"] == 24, before["_meta"]
    assert after["_meta"]["migrations"] == 52, after["_meta"]
    assert after["_meta"]["property_count"] == before["_meta"]["property_count"] == 2
    for field in ("staff_count", "reservation_count", "payment_kgs", "folio_kgs", "orders_kgs"):
        assert before["_meta"][field] == after["_meta"][field], field
    changed = []
    for table, oldrows in before.items():
        if table == "_meta":
            continue
        assert table in after, f"Missing original table {table}"
        for key, fields in oldrows.items():
            newrow = after[table].get(key)
            assert newrow is not None, f"Lost row {table}:{key}"
            for name, value in fields.items():
                if newrow.get(name) != value:
                    changed.append((table, key, name))
    # Migration #560 documented ONLY property timestamps as permissible touched fields.
    unexpected = [c for c in changed if (c[0], c[2]) != ("properties", "updatedAt")]
    assert not unexpected, f"Original fields changed unexpectedly: {unexpected[:12]}"
    print("MIGRATION_ROW_AND_FINANCE_PRESERVATION_PASS", json.dumps({
        "legacy_tables": len(before) - 1, "current_tables": len(after) - 1,
        "legacy_migrations": 24, "current_migrations": 52,
        "allowed_timestamp_changes": len(changed), "unexpected_changes": 0,
    }))


async def verify_http(code: str, port: int):
    assert code in ("ALPHA", "BETA")
    base = f"http://127.0.0.1:{port}"
    conn = await asyncpg.connect(os.environ["MARINA_LEGACY_NEW_DB"])
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", code)
        assert pid
        expected = {
            str(row["id"]) for row in await conn.fetch(
                'SELECT id FROM staff_users WHERE "propertyId"=$1', pid)
        }
    finally:
        await conn.close()
    with httpx.Client(base_url=base, timeout=20.0, trust_env=False) as client:
        resp = client.get("/api/v1/site/content?locale=ru")
        assert resp.status_code == 200, (code, resp.status_code, resp.text[:300])
        data = resp.json()
        assert data["property"] == code and data["source"] == "DATABASE"
        assert data["published_version"] == 1
        assert data["content"]["hero"]["title"] == "Synthetic Hotel " + code
        assert data["content"]["hero"]["subtitle"] == "Welcome to synthetic Hotel " + code
        assert data["content"]["contacts"]["email"] == code.lower() + "@example.test"
        assert set(data["content"]) == {"hero", "contacts", "seo"}

        html = client.get("/api/v1/site/customer-page?locale=ru")
        assert html.status_code == 200, (code, html.status_code, html.text[:300])
        assert "Synthetic Hotel " + code in html.text
        assert ("Synthetic Hotel BETA" if code == "ALPHA" else "Synthetic Hotel ALPHA") not in html.text
        assert "3korony" not in html.text.lower()
        rooms = client.get("/api/v1/site/customer-rooms?locale=ru")
        assert rooms.status_code == 200 and "Standard" in rooms.text
        assert "3korony" not in rooms.text.lower()
        legacy_language = client.get("/api/v1/site/customer-rooms?lang=ru")
        assert legacy_language.status_code == 200 and "Standard" in legacy_language.text
        unpublished = client.get("/api/v1/site/customer-page?locale=en")
        assert unpublished.status_code == 200
        assert unpublished.headers.get("x-robots-tag") == "noindex, nofollow"
        assert code + "@example.test" not in unpublished.text

        owner = httpx.Client(base_url=base, timeout=20, trust_env=False)
        dining = httpx.Client(base_url=base, timeout=20, trust_env=False)
        try:
            for sess, username in [(owner, "owner"), (dining, "dining_staff")]:
                login = sess.post("/api/v1/auth/login", json={
                    "username": username, "password": "Synthetic-audit-only-2026!"
                })
                assert login.status_code == 200, (code, username, login.status_code, login.text[:250])
            overview = owner.get("/api/v1/admin/staff/overview")
            assert overview.status_code == 200, (code, overview.status_code)
            found = {item["id"] for item in overview.json()["staff"]}
            assert found == expected, (code, len(found), len(expected))
            me = dining.get("/api/v1/auth/me")
            assert me.status_code == 200 and me.json()["role"] == "DINING_STAFF"
            dining_id = me.json()["id"]
            assert dining.get("/api/v1/kitchen/orders").status_code == 403
            change = owner.patch(f"/api/v1/admin/staff/{dining_id}", json={"role": "COOK"})
            assert change.status_code == 200 and change.json()["id"] == dining_id
            assert dining.get("/api/v1/auth/me").status_code == 401
            assert dining.post("/api/v1/auth/login", json={
                "username": "dining_staff", "password": "Synthetic-audit-only-2026!"
            }).status_code == 200
            assert dining.get("/api/v1/kitchen/orders").status_code == 200
            assert dining.get("/api/v1/dining/floor").status_code == 403
        finally:
            owner.close()
            dining.close()
    print("HOTEL_PUBLISHED_SITE_AND_LEGACY_STAFF_PASS", code, "port", port)


async def main():
    mode = sys.argv[1]
    assert os.environ.get("MARINA_MIGRATION_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_OLD_TO_564"
    for name in ("MARINA_LEGACY_OLD_DB", "MARINA_LEGACY_NEW_DB", "MARINA_LEGACY_ROLLBACK_DB"):
        url = os.environ[name]
        assert "127.0.0.1" in url and "/marina_" in url and "production" not in url.lower()
    if mode == "snapshot":
        await snapshot_stage(sys.argv[2])
    elif mode == "compare":
        verify_preservation()
    elif mode == "http":
        await verify_http(sys.argv[2], int(sys.argv[3]))
    else:
        raise SystemExit(f"Unknown mode {mode}")


if __name__ == "__main__":
    asyncio.run(main())
