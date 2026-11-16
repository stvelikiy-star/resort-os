"""Explicit localhost-only PostgreSQL E2E for stay nights and served/folio revenue sources.

Never creates customer Payment or recognized income. All fixture rows deleted.
"""
import asyncio
import os
import uuid
from datetime import timedelta
import asyncpg
import httpx


def check(r,status,label):
    assert r.status_code==status,(label,r.status_code,r.text)
    return r.json()


async def main():
    if os.getenv("ALLOW_OWNER_EXPENSE_TEST_WRITES")!="1":
        raise RuntimeError("Requires disposable PostgreSQL opt-in")
    url=os.environ["DATABASE_URL"].split("?",1)[0]
    base=os.getenv("CORE_API_URL","http://127.0.0.1:8000")
    if not ("@localhost:" in url or "@127.0.0.1:" in url) or not base.startswith("http://127.0.0.1:"):
        raise RuntimeError("Remote hotel DB/API forbidden")
    db=await asyncpg.connect(url)
    rid=gid=sid=aid=oid=fid=unlinked_id=None
    pid=None
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner, \
                   httpx.AsyncClient(base_url=base,timeout=30) as cook:
            check(await owner.post("/api/v1/auth/login",json={
                "username":os.environ["BOOTSTRAP_OWNER_USERNAME"],
                "password":os.environ["BOOTSTRAP_OWNER_PASSWORD"]}),200,"owner login")
            check(await cook.post("/api/v1/auth/login",json={
                "username":os.environ["KITCHEN_MENU_DINING_USERNAME"],
                "password":os.environ["KITCHEN_MENU_DINING_PASSWORD"]}),200,"cook login")
            me=check(await owner.get("/api/v1/auth/me"),200,"owner me")
            pid=await db.fetchval("SELECT id FROM properties WHERE code=$1",me["property_code"])
            room=await db.fetchval('SELECT id FROM rooms WHERE "propertyId"=$1 LIMIT 1',pid)
            assert room,"isolated seeded hotel must have a room"
            today=await db.fetchval(
                "SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1",pid)
            before_payment_count=await db.fetchval("SELECT COUNT(*) FROM payments")
            start=today-timedelta(days=3)
            code=uuid.uuid4().hex[:10]
            rid=uuid.uuid4();gid=uuid.uuid4();sid=uuid.uuid4();aid=uuid.uuid4()
            oid=uuid.uuid4();fid=uuid.uuid4();unlinked_id=uuid.uuid4()
            await db.execute(
                '''INSERT INTO guests (id,"propertyId","firstName","updatedAt")
                   VALUES($1,$2,$3,now())''',gid,pid,"Synthetic Revenue Delivery E2E")
            await db.execute(
                '''INSERT INTO reservations
                   (id,"propertyId","bookingNumber","primaryGuestId",status,
                    "checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt")
                   VALUES($1,$2,$3,$4,'CHECKED_OUT',$5,$6,1,0,1000,now(),now())''',
                rid,pid,"DELIVERED-"+code,gid,start,today)
            # Actual UTC-naive datetimes are explicitly converted from local
            # property date; match the app's legacy TIMESTAMP(3) storage.
            actual_in,actual_out=await db.fetchrow(
                '''SELECT (($1::date + time '14:00') AT TIME ZONE p.timezone)
                      AT TIME ZONE 'UTC' AS ain,
                          (($2::date + time '11:00') AT TIME ZONE p.timezone)
                      AT TIME ZONE 'UTC' AS aout
                   FROM properties p WHERE id=$3''',start,today,pid)
            await db.execute(
                '''INSERT INTO stays(id,"propertyId","reservationId","guestId",
                        status,"actualCheckInAt","actualCheckOutAt","updatedAt")
                   VALUES($1,$2,$3,$4,'CHECKED_OUT',$5,$6,now())''',
                sid,pid,rid,gid,actual_in,actual_out)
            await db.execute(
                '''INSERT INTO room_assignments
                   (id,"propertyId","stayId","roomId","startedAt","endedAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6,now())''',
                aid,pid,sid,room,actual_in,actual_out)
            await db.execute(
                '''INSERT INTO kitchen_orders
                   (id,"propertyId","orderNumber",status,source,"reservationId",
                    "guestCount","totalKgs","openedAt","completedAt","createdAt","updatedAt")
                   VALUES($1,$2,$3,'SERVED','RECEPTION',$4,1,350,now(),now(),now(),now())''',
                oid,pid,"DELIVERY-E2E-"+code,rid)
            await db.execute(
                '''INSERT INTO guest_folio_charges
                   (id,"propertyId","reservationId","stayId","guestId",
                    "sourceType","sourceId",code,description,"amountKgs",
                    status,"serviceDate","createdByType","createdAt","updatedAt")
                   VALUES($1,$2,$3,$4,$5,'KITCHEN_ORDER',$6,'DINING_ORDER',
                       'Synthetic served meal',350,'OPEN',$7,'STAFF',now(),now())''',
                fid,pid,rid,sid,gid,oid,today)
            await db.execute(
                '''UPDATE kitchen_orders SET "folioChargeId"=$2 WHERE id=$1''',
                oid,fid)
            await db.execute(
                '''INSERT INTO kitchen_orders
                   (id,"propertyId","orderNumber",status,source,
                    "guestCount","totalKgs","openedAt","completedAt","createdAt","updatedAt")
                   VALUES($1,$2,$3,'SERVED','RECEPTION',1,100,now(),now(),now(),now())''',
                unlinked_id,pid,"DELIVERY-UNLINKED-"+code)
            endpoint="/api/v1/admin/finance/owner/delivered-revenue-sources"
            params={"from_date":start.isoformat(),"to_date":today.isoformat()}
            check(await cook.get(endpoint,params=params),403,"cook denied")
            before=check(await owner.get(endpoint,params=params),200,"source nightly")
            accomod=before["accommodation"]
            actual_days=[r for r in accomod["night_preview"] if r["reservation_id"]==str(rid)]
            assert [(r["service_date"],int(r["allocated_booking_face_value_kgs"]))
                    for r in actual_days]==[(start.isoformat(),334),
                                           ((start+timedelta(days=1)).isoformat(),333),
                                           ((start+timedelta(days=2)).isoformat(),333)]
            assert before["dining"]["served_with_matching_folio_count"]>=1
            assert before["dining"]["excluded_orders_count"]>=1
            assert before["dining"]["exclusion_reasons"]["SERVED_ORDER_NOT_LINKED_TO_FOLIO"]>=1
            assert before["recognition"]["recognized_total_revenue_kgs"] is None
            assert before["recognition"]["automatic_posting"] is False
            narrow=check(await owner.get(endpoint,params={
                "from_date":start.isoformat(),"to_date":start.isoformat()
            }),200,"partial nightly period")
            rows=[r for r in narrow["accommodation"]["night_preview"]
                  if r["reservation_id"]==str(rid)]
            assert len(rows)==1 and rows[0]["allocated_booking_face_value_kgs"]=="334"
            summary=check(await owner.get("/api/v1/admin/finance/owner/accrual-readiness",
                                           params=params),200,"accrual integration")
            source=summary["delivered_revenue_sources"]
            assert source["accommodation"]["delivered_booked_nights_count"]>=3
            assert source["dining"]["kitchen_and_folio_double_counted"] is False
            assert summary["recognition"]["recognized_profit_kgs"] is None
            # Changed folio price must block an order from the valid candidate,
            # not synthesize additional amount or touch Payment.
            await db.execute('UPDATE guest_folio_charges SET "amountKgs"=351 WHERE id=$1',fid)
            mismatched=check(await owner.get(endpoint,params=params),200,"mismatched folio")
            assert mismatched["dining"]["exclusion_reasons"]["FOLIO_AMOUNT_MISMATCH"]>=1
            await db.execute('UPDATE guest_folio_charges SET "amountKgs"=350,status=\'WAIVED\' WHERE id=$1',fid)
            waived=check(await owner.get(endpoint,params=params),200,"waived folio")
            assert waived["dining"]["exclusion_reasons"]["FOLIO_VOID_OR_WAIVED"]>=1
            assert await db.fetchval("SELECT COUNT(*) FROM payments")==before_payment_count
            check(await owner.get(endpoint,params={
                "from_date":today.isoformat(),"to_date":start.isoformat()
            }),422,"reject backwards date range")
            print("DELIVERED_REVENUE_POSTGRES_PASS: 334+333+333 nightly "
                  "partial reports, exactly one served folio, missing/mismatch/"
                  "waived blocked, no Payment or recognized profit")
    finally:
        if pid:
            # All effects are synthetic and isolated. FK-safe reverse order.
            if fid:
                await db.execute('UPDATE kitchen_orders SET "folioChargeId"=NULL WHERE id=$1',oid)
                await db.execute('DELETE FROM guest_folio_charges WHERE id=$1',fid)
            for x in (oid,unlinked_id):
                if x:await db.execute('DELETE FROM kitchen_orders WHERE id=$1',x)
            if aid:await db.execute('DELETE FROM room_assignments WHERE id=$1',aid)
            if sid:await db.execute('DELETE FROM stays WHERE id=$1',sid)
            if rid:await db.execute('DELETE FROM reservations WHERE id=$1',rid)
            if gid:await db.execute('DELETE FROM guests WHERE id=$1',gid)
        await db.close()


if __name__=="__main__":
    asyncio.run(main())
