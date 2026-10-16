"""Exercise real channel imports in the disposable two-property CI runtimes."""
import asyncio
import csv
import io
from datetime import date, timedelta
import os
import uuid

import asyncpg
import httpx
from argon2 import PasswordHasher

from marina_two_property_restore_e2e import validate_ci_dsn


async def main():
    dsn = validate_ci_dsn(os.environ["MARINA_STAGING_DATABASE_URL"])
    async with httpx.AsyncClient(base_url=os.environ["MARINA_STAGING_BASE_URL"], timeout=20) as a, httpx.AsyncClient(base_url=os.environ["MARINA_STAGING_TENANT_B_BASE_URL"], timeout=20) as b:
        for client, letter in ((a, "A"), (b, "B")):
            login = await client.post("/api/v1/auth/login", json={"username": os.environ[f"MARINA_STAGING_TENANT_{letter}_USERNAME"], "password": os.environ[f"MARINA_STAGING_TENANT_{letter}_PASSWORD"]})
            assert login.status_code == 200, login.text
        ca, cb = await a.get("/api/v1/admin/channels"), await b.get("/api/v1/admin/channels")
        assert ca.status_code == cb.status_code == 200
        assert all(not item["connected"] and not item["automatic_sync"] for item in ca.json()["providers"])
        rooms_a, rooms_b = ca.json()["rooms"], cb.json()["rooms"]
        external = "CI-" + uuid.uuid4().hex
        offset = 30 if dsn == validate_ci_dsn(os.environ["RESTORE_DATABASE_URL"]) else 10
        start, end = date.today() + timedelta(days=offset), date.today() + timedelta(days=offset + 2)
        payload = {"provider": "BOOKING_COM", "external_id": external, "revision": 1, "room_id": rooms_a[0]["id"], "guest_name": "Synthetic OTA guest", "check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 1, "children": 0, "total_kgs": 9000}
        async def send(client, data, expected=200):
            response = await client.post("/api/v1/admin/channels/reservations/import", json=data)
            assert response.status_code == expected, (response.status_code, response.text)
            return response.json()
        first, duplicate = await asyncio.gather(send(a, payload), send(a, payload))
        assert first["reservation_id"] == duplicate["reservation_id"]
        assert sorted([first["duplicate"], duplicate["duplicate"]]) == [False, True]
        reservation_id = uuid.UUID(first["reservation_id"])
        conn = await asyncpg.connect(dsn)
        try:
            initial_guest = await conn.fetchval('SELECT "primaryGuestId" FROM reservations WHERE id=$1', reservation_id)
            assert await conn.fetchval('SELECT count(*) FROM payments WHERE "reservationId"=$1', reservation_id) == 0
            assert await conn.fetchval('SELECT count(*) FROM inventory_blocks WHERE "reservationId"=$1 AND active=true', reservation_id) == 1
            grid = (await a.get("/api/v1/pms/grid", params={"start": start.isoformat(), "end": end.isoformat()})).json()
            blocks = [block for room in grid["rooms"] for block in room["blocks"] if block["reservation_id"] == str(reservation_id)]
            assert len(blocks) == 1 and blocks[0]["channel_source"] == "Booking.com"
            assert external in blocks[0]["reason"]
            conflict = await send(a, {**payload, "external_id": external + "-conflict"}, 409)
            assert conflict["detail"]["code"] == "CHANNEL_ROOM_CONFLICT"
            updated = {**payload, "revision": 2, "room_id": rooms_a[1]["id"], "total_kgs": 10000}
            change = await send(a, updated)
            assert change["reservation_id"] == str(reservation_id)
            assert await conn.fetchval('SELECT "primaryGuestId" FROM reservations WHERE id=$1', reservation_id) == initial_guest
            assert await conn.fetchval('SELECT count(*) FROM inventory_blocks WHERE "reservationId"=$1 AND active=true', reservation_id) == 1
            assert (await send(a, payload, 409))["detail"]["code"] == "CHANNEL_STALE_REVISION"
            assert (await send(a, {**updated, "total_kgs": 10001}, 409))["detail"]["code"] == "CHANNEL_REVISION_PAYLOAD_MISMATCH"
            await send(a, {**payload, "external_id": external + "-foreign", "room_id": rooms_b[0]["id"]}, 404)
            await send(a, {**payload, "currency": "USD"}, 422)
            await send(a, {**payload, "property_id": str(uuid.uuid4())}, 422)
            capacity = await send(a, {**payload, "external_id": external + "-capacity", "adults": 20}, 409)
            assert capacity["detail"]["code"] == "CHANNEL_ROOM_CAPACITY"
            blocked_id = uuid.UUID(rooms_a[2]["id"])
            await conn.execute('UPDATE rooms SET "operationalState"=\'TECH_BLOCK\' WHERE id=$1', blocked_id)
            try:
                tech = await send(a, {**payload, "external_id": external + "-tech", "room_id": str(blocked_id)}, 409)
                assert tech["detail"]["code"] == "CHANNEL_ROOM_TECH_BLOCK"
            finally:
                await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\' WHERE id=$1', blocked_id)
            parallel = await asyncio.gather(*[a.post("/api/v1/admin/channels/reservations/import", json={**payload, "external_id": external + suffix, "room_id": rooms_a[3]["id"]}) for suffix in ("-race-1", "-race-2")])
            assert sorted(result.status_code for result in parallel) == [200, 409]
            other = await send(b, {**payload, "room_id": rooms_b[0]["id"]})
            assert other["reservation_id"] != str(reservation_id)
            items_a = (await a.get("/api/v1/admin/channels")).json()["items"]
            assert other["reservation_id"] not in {item["reservation_id"] for item in items_a}
            cancellation = {"provider": payload["provider"], "external_id": external, "revision": 3, "status": "CANCELLED"}
            await send(a, cancellation)
            assert (await send(a, cancellation))["duplicate"] is True
            assert await conn.fetchval('SELECT status::text FROM reservations WHERE id=$1', reservation_id) == "CANCELLED"
            assert await conn.fetchval('SELECT count(*) FROM inventory_blocks WHERE "reservationId"=$1 AND active=true', reservation_id) == 0
            assert await conn.fetchval('SELECT count(*) FROM payments WHERE "reservationId"=$1', reservation_id) == 0
            assert (await send(a, {**updated, "revision": 4}, 409))["detail"]["code"] == "CHANNEL_CANCELLED_REQUIRES_REVIEW"
            await send(a, {**cancellation, "external_id": external + "-tombstone", "revision": 4})
            assert (await send(a, {**payload, "external_id": external + "-tombstone", "revision": 3}, 409))["detail"]["code"] == "CHANNEL_STALE_REVISION"
            def batch_csv(items):
                buffer = io.StringIO()
                keys = sorted(set().union(*(item.keys() for item in items)))
                writer = csv.DictWriter(buffer, fieldnames=keys)
                writer.writeheader()
                writer.writerows(items)
                return buffer.getvalue()
            batch_one = {**payload, "external_id": external + "-batch-a", "room_id": rooms_a[4]["id"]}
            batch_two = {**payload, "external_id": external + "-batch-b", "room_id": rooms_a[5]["id"]}
            csv_text = batch_csv([batch_one, batch_two])
            async def csv_send(text, preview=True, expected=200):
                response = await a.post("/api/v1/admin/channels/reservations/csv", json={"csv_text": text, "preview": preview})
                assert response.status_code == expected, response.text
                return response.json()
            async def counts():
                return tuple([await conn.fetchval(f'SELECT count(*) FROM {table}') for table in ("reservations", "reservation_requests", "guests", "inventory_blocks", "automation_inbound_events", "audit_logs", "payments")])
            before = await counts()
            assert (await csv_send(csv_text))["mode"] == "PREVIEW"
            assert await counts() == before, "Preview must leave every canonical/identity/audit table unchanged"
            bad_batch = batch_csv([batch_one, {**batch_two, "room_id": batch_one["room_id"]}])
            assert (await csv_send(bad_batch, False, 409))["detail"]["row"] == 3
            assert await counts() == before, "Failed batch must roll back earlier rows"
            await csv_send(batch_csv([batch_one, {**batch_two, "room_id": rooms_b[0]["id"]}]), False, 404)
            assert await counts() == before, "Foreign-room rejection must roll back earlier rows"
            imported = await csv_send(csv_text, False)
            assert imported["mode"] == "IMPORTED" and imported["count"] == 2
            assert all(not item["duplicate"] for item in imported["items"])
            after = await counts()
            assert after[0] == before[0] + 2 and after[-1] == before[-1]
            replay = await csv_send(csv_text, False)
            assert all(item["duplicate"] for item in replay["items"])
            assert await counts() == after
            ma = (await a.get("/api/v1/admin/channels/mappings")).json()
            mb = (await b.get("/api/v1/admin/channels/mappings")).json()
            assert ma["connected"] is False and ma["automatic_sync"] is False
            mapping = {"provider": "BOOKING_COM", "external_property_id": external, "external_room_type_id": "category", "external_rate_plan_id": "standard", "room_type_id": ma["room_types"][0]["id"], "rate_plan_id": ma["rate_plans"][0]["id"]}
            async def map_send(client, body, expected=200):
                result = await client.put("/api/v1/admin/channels/mappings", json=body)
                assert result.status_code == expected, result.text
                return result.json()
            parallel_maps = await asyncio.gather(*[a.put("/api/v1/admin/channels/mappings", json=mapping) for _ in range(2)])
            assert sorted(result.status_code for result in parallel_maps) == [200, 409]
            saved_map = next(result.json() for result in parallel_maps if result.status_code == 200)
            assert saved_map["revision"] == 1 and saved_map["connected"] is False
            await map_send(a, {**mapping, "external_property_id": external + "-foreign-room", "room_type_id": mb["room_types"][0]["id"]}, 404)
            await map_send(a, {**mapping, "external_property_id": external + "-foreign-rate", "rate_plan_id": mb["rate_plans"][0]["id"]}, 404)
            await map_send(a, {**mapping, "property_id": str(uuid.uuid4())}, 422)
            await map_send(a, {**mapping, "currency": "USD"}, 422)
            updated_map = await map_send(a, {**mapping, "active": False, "expected_revision": 1})
            assert updated_map["id"] == saved_map["id"] and updated_map["revision"] == 2 and updated_map["active"] is False
            assert (await map_send(a, {**mapping, "expected_revision": 1}, 409))["detail"]["code"] == "CHANNEL_MAPPING_STALE"
            b_map = await map_send(b, {**mapping, "room_type_id": mb["room_types"][0]["id"], "rate_plan_id": mb["rate_plans"][0]["id"]})
            assert b_map["id"] != saved_map["id"]
            assert b_map["id"] not in {row["id"] for row in (await a.get("/api/v1/admin/channels/mappings")).json()["items"]}
            # Composite foreign keys enforce tenant boundaries even below HTTP.
            try:
                await conn.execute('UPDATE channel_mappings SET "roomTypeId"=$2 WHERE id=$1', uuid.UUID(saved_map["id"]), uuid.UUID(mb["room_types"][0]["id"]))
                raise AssertionError("Foreign room type accepted by database")
            except asyncpg.ForeignKeyViolationError:
                pass
            me = (await a.get("/api/v1/auth/me")).json()
            for role in ("AGENT", "RECEPTION"):
                username = "channel-ci-" + uuid.uuid4().hex[:12]
                password = "Synthetic-Channel-Role-2026!"
                await conn.execute('INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt") VALUES ($1,$2,$3,$3,$4,$5::"StaffRole",true,now(),now())', uuid.uuid4(), uuid.UUID(me["property_id"]), username, PasswordHasher().hash(password), role)
                async with httpx.AsyncClient(base_url=os.environ["MARINA_STAGING_BASE_URL"]) as limited:
                    login = await limited.post("/api/v1/auth/login", json={"username": username, "password": password})
                    assert login.status_code == 200, login.text
                    assert (await limited.get("/api/v1/admin/channels")).status_code == 403
                    assert (await limited.get("/api/v1/admin/channels/mappings")).status_code == 403
                    await map_send(limited, mapping, 403)
                    assert (await limited.post("/api/v1/admin/channels/reservations/csv", json={"csv_text": csv_text})).status_code == 403
                    await send(limited, {**payload, "external_id": external + role}, 403)
        finally:
            await conn.close()
    print("MARINA_CHANNEL_RESERVATIONS_E2E_PASS: create/replay/update/cancel, concurrency, room conflicts, revision guards, property isolation, RBAC, CSV rollback/preview, mapping revision/property/FK guards and no fabricated payments")


if __name__ == "__main__":
    asyncio.run(main())
