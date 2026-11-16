"""Disposable localhost-only approval journal PostgreSQL E2E.

This test intentionally retains synthetic source evidence until the CI
PostgreSQL service is destroyed: the immutable event must never reference a
deleted synthetic stay/order. Never run against real hotel or production.
"""
import asyncio
import os
import uuid
from datetime import timedelta

import asyncpg
import httpx


def accept(r,status,label):
    assert r.status_code==status,(label,r.status_code,r.text)
    return r.json()


async def main():
    if os.getenv("ALLOW_REVENUE_JOURNAL_SYNTHETIC_CI")!="1":
        raise RuntimeError("Requires explicit disposable synthetic CI database")
    database=os.environ["DATABASE_URL"].split("?",1)[0]
    base=os.getenv("CORE_API_URL","http://127.0.0.1:8000")
    if not ("@localhost:" in database or "@127.0.0.1:" in database):
        raise RuntimeError("Refusing non-local DB")
    if not base.startswith("http://127.0.0.1:"):
        raise RuntimeError("Refusing non-local API")
    db=await asyncpg.connect(database)
    try:
        async with httpx.AsyncClient(base_url=base,timeout=40) as owner, \
                   httpx.AsyncClient(base_url=base,timeout=40) as cook:
            accept(await owner.post('/api/v1/auth/login',json={
                'username':os.environ['BOOTSTRAP_OWNER_USERNAME'],
                'password':os.environ['BOOTSTRAP_OWNER_PASSWORD']}),200,'owner auth')
            accept(await cook.post('/api/v1/auth/login',json={
                'username':os.environ['KITCHEN_MENU_DINING_USERNAME'],
                'password':os.environ['KITCHEN_MENU_DINING_PASSWORD']}),200,'cook auth')
            me=accept(await owner.get('/api/v1/auth/me'),200,'owner')
            pid=await db.fetchval('SELECT id FROM properties WHERE code=$1',me['property_code'])
            room=await db.fetchval('SELECT id FROM rooms WHERE "propertyId"=$1 LIMIT 1',pid)
            assert room,'CI requires synthetic seeded room'
            today=await db.fetchval(
                'SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1',pid)
            start=today-timedelta(days=3)
            before_payments=await db.fetchval('SELECT COUNT(*) FROM payments')
            marker=uuid.uuid4().hex[:12]
            rid=uuid.uuid4();gid=uuid.uuid4();sid=uuid.uuid4();aid=uuid.uuid4()
            oid=uuid.uuid4();fid=uuid.uuid4()
            # All sources are created ONLY in a disposable CI PostgreSQL.
            await db.execute(
                '''INSERT INTO guests (id,"propertyId","firstName","updatedAt")
                   VALUES($1,$2,$3,now())''',gid,pid,'Journal Synthetic CI')
            await db.execute(
                '''INSERT INTO reservations
                   (id,"propertyId","bookingNumber","primaryGuestId",status,
                    "checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt")
                   VALUES($1,$2,$3,$4,'CHECKED_OUT',$5,$6,1,0,1000,now(),now())''',
                rid,pid,'APPROVAL-'+marker,gid,start,today)
            times=await db.fetchrow(
                '''SELECT (($1::date + time '14:00') AT TIME ZONE p.timezone)
                      AT TIME ZONE 'UTC' AS ain,
                          (($2::date + time '11:00') AT TIME ZONE p.timezone)
                      AT TIME ZONE 'UTC' AS aout
                   FROM properties p WHERE id=$3''',start,today,pid)
            await db.execute(
                '''INSERT INTO stays(id,"propertyId","reservationId","guestId",
                    status,"actualCheckInAt","actualCheckOutAt","updatedAt")
                    VALUES($1,$2,$3,$4,'CHECKED_OUT',$5,$6,now())''',
                sid,pid,rid,gid,times['ain'],times['aout'])
            await db.execute(
                '''INSERT INTO room_assignments
                    (id,"propertyId","stayId","roomId","startedAt","endedAt","updatedAt")
                    VALUES ($1,$2,$3,$4,$5,$6,now())''',
                aid,pid,sid,room,times['ain'],times['aout'])
            await db.execute(
                '''INSERT INTO kitchen_orders
                    (id,"propertyId","orderNumber",status,source,"reservationId",
                     "guestCount","totalKgs","openedAt","completedAt","createdAt","updatedAt")
                    VALUES($1,$2,$3,'SERVED','RECEPTION',$4,1,350,now(),now(),now(),now())''',
                oid,pid,'APPROVAL-DINING-'+marker,rid)
            await db.execute(
                '''INSERT INTO guest_folio_charges
                   (id,"propertyId","reservationId","stayId","guestId",
                    "sourceType","sourceId",code,description,"amountKgs",
                    status,"serviceDate","createdByType","createdAt","updatedAt")
                   VALUES($1,$2,$3,$4,$5,'KITCHEN_ORDER',$6,'DINING_ORDER',
                     'Synthetic approval meal',350,'OPEN',$7,'STAFF',now(),now())''',
                fid,pid,rid,sid,gid,oid,today)
            await db.execute('UPDATE kitchen_orders SET "folioChargeId"=$2 WHERE id=$1',oid,fid)
            route='/api/v1/admin/finance/owner/revenue-source-events'
            accrual_url='/api/v1/admin/finance/owner/accrual-readiness'
            accrual_period={'from_date':start.isoformat(),'to_date':today.isoformat()}
            baseline=accept(await owner.get(accrual_url,params=accrual_period),
                            200,'owner baseline journal snapshot')
            baseline_journal=baseline['source_approval_journal']
            assert baseline_journal['recognized_profit_kgs'] is None
            r1=uuid.uuid4()
            approval={'id':str(r1),'source_type':'ROOM_NIGHT',
                      'source_id':str(rid),'service_date':start.isoformat(),
                      'reason':'Checked actual night and room assignment'}
            accept(await cook.post(route,json=approval),403,'cook cannot approve')
            accept(await cook.get(route,params={
                'from_date':start.isoformat(),'to_date':today.isoformat()
            }),403,'cook cannot read journal')
            responses=await asyncio.gather(*[owner.post(route,json=approval) for _ in range(8)])
            assert all(r.status_code==201 for r in responses),[
                (r.status_code,r.text) for r in responses]
            data=[r.json() for r in responses]
            assert sum(not x['already_processed'] for x in data)==1
            assert all(x['face_value_kgs']=='334.0000' for x in data)
            assert all(x['recognized_revenue_kgs'] is None for x in data)
            assert all(x['customer_payment_created'] is False for x in data)
            accept(await owner.post(route,json={**approval,
                'reason':'Modified source approval reason'}),409,'changed ID rejected')
            accept(await owner.post(route,json={**approval,'id':str(uuid.uuid4())}),
                   409,'duplicate room-night source rejected')
            accept(await owner.post(route,json={**approval,'id':str(uuid.uuid4()),
                'service_date':today.isoformat()}),409,'checkout day excluded')
            # One verified night can be independently approved for the next date.
            second=accept(await owner.post(route,json={**approval,
                'id':str(uuid.uuid4()),
                'service_date':(start+timedelta(days=1)).isoformat()}),201,'next night')
            assert second['face_value_kgs']=='333.0000'
            dining={'id':str(uuid.uuid4()),'source_type':'DINING_ORDER',
                    'source_id':str(oid),'service_date':today.isoformat(),
                    'reason':'Served kitchen order matched to active folio'}
            meal=accept(await owner.post(route,json=dining),201,'served order source')
            assert meal['face_value_kgs']=='350.0000'
            assert meal['recognized_revenue_kgs'] is None
            reverse_id=uuid.uuid4()
            reverse={'id':str(reverse_id),'reason':'Source requires accounting adjustment'}
            rr=await asyncio.gather(*[owner.post(route+'/'+str(r1)+'/reverse',
                                                  json=reverse) for _ in range(8)])
            assert all(r.status_code==201 for r in rr),[(r.status_code,r.text) for r in rr]
            assert sum(not r.json()['already_processed'] for r in rr)==1
            accept(await owner.post(route+'/'+str(r1)+'/reverse',
                json={**reverse,'reason':'Changed reversal request'}),409,
                   'changed reversal same ID rejected')
            accept(await owner.post(route+'/'+str(r1)+'/reverse',
                json={'id':str(uuid.uuid4()),'reason':'Second reversal denied'}),409,
                   'cannot reverse twice')
            # Approval remains immutable even after reversal; cannot reuse source.
            accept(await owner.post(route,json={**approval,'id':str(uuid.uuid4())}),
                   409,'reapproved source forbidden')
            events=accept(await owner.get(route,params={
                'from_date':start.isoformat(),'to_date':today.isoformat()}),200,
                'journal history')
            ids=[x['id'] for x in events['items']]
            assert ids.count(str(r1))==1 and ids.count(str(reverse_id))==1
            assert events['history_append_only'] is True
            assert events['recognized_profit_kgs'] is None
            snapshot=accept(await owner.get(accrual_url,params=accrual_period),
                            200,'owner financial approval snapshot')
            ledger=snapshot['source_approval_journal']
            assert ledger['approval_events_count']-baseline_journal['approval_events_count']==3
            assert ledger['reversal_events_count']-baseline_journal['reversal_events_count']==1
            assert ledger['active_room_nights_count']-baseline_journal['active_room_nights_count']==1
            assert ledger['active_served_dining_count']-baseline_journal['active_served_dining_count']==1
            assert ledger['recognized_revenue_kgs'] is None
            assert snapshot['recognition']['recognized_profit_kgs'] is None
            stored=await db.fetchval(
                'SELECT COUNT(*) FROM owner_revenue_source_events WHERE "propertyId"=$1 AND id=$2',
                pid,r1)
            assert stored==1
            try:
                await db.execute(
                    'UPDATE owner_revenue_source_events SET reason=$1 WHERE id=$2',
                    'Illegal rewrite',r1)
                raise AssertionError('UPDATE must fail on immutable journal')
            except asyncpg.PostgresError as exc:
                assert 'OWNER_REVENUE_SOURCE_IMMUTABLE' in str(exc)
            try:
                await db.execute('DELETE FROM owner_revenue_source_events WHERE id=$1',r1)
                raise AssertionError('DELETE must fail on immutable journal')
            except asyncpg.PostgresError as exc:
                assert 'OWNER_REVENUE_SOURCE_IMMUTABLE' in str(exc)
            assert await db.fetchval('SELECT COUNT(*) FROM payments')==before_payments
            print('REVENUE_SOURCE_JOURNAL_POSTGRES_PASS: 8-way same ID approval '
                  'and reversal, source/date unique, 334+333 nights, served folio, '
                  'non-owner 403, immutable UPDATE/DELETE denied, no Payment')
    finally:
        # No DELETE of approvals or source entities by design; disposable CI DB
        # lifetime is the retention boundary for this synthetic-only test.
        await db.close()


if __name__=='__main__':
    asyncio.run(main())
