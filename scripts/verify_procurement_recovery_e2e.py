"""Disposable PostgreSQL: same-ID races and real mobile journal process recovery."""
import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
import asyncpg
import httpx


def checked(r,status=200):
    assert r.status_code==status,(status,r.status_code,r.text)
    return r.json()

async def login(client,name,password):
    r=await client.post('/api/v1/auth/login',json={'username':name,'password':password})
    me=checked(r);client.headers['Cookie']='; '.join(f'{k}={v}' for k,v in r.cookies.items());return me

async def main():
    base=os.environ.get('CORE_API_URL','http://127.0.0.1:8000');url=os.environ['DATABASE_URL'].split('?',1)[0]
    if os.environ.get('ALLOW_PROCUREMENT_RECOVERY_TEST_WRITES')!='1' or urlparse(base).hostname not in {'localhost','127.0.0.1'} or urlparse(url).hostname not in {'localhost','127.0.0.1'}:
        raise RuntimeError('Explicit disposable localhost opt-in required')
    db=await asyncpg.connect(url)
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner,httpx.AsyncClient(base_url=base,timeout=30) as store:
            me=await login(owner,os.environ['BOOTSTRAP_OWNER_USERNAME'],os.environ['BOOTSTRAP_OWNER_PASSWORD'])
            actor=await login(store,os.environ['PROC_STORE_USERNAME'],os.environ['PROC_STORE_PASSWORD'])
            pid=await db.fetchval('SELECT id FROM properties WHERE code=$1',me['property_code'])
            payments=await db.fetchval('SELECT count(*) FROM payments')
            items=[]
            for _ in range(2):
                items.append(checked(await owner.post('/api/v1/kitchen/stock/items',json={'name':'Recovery '+uuid.uuid4().hex,'unit':'KG','cost_per_unit_kgs':'10','is_sample':False}),201)['id'])
            root='/api/v1/kitchen/procurement/requests'
            def payload(item,opid=None):return {'request_id':opid or str(uuid.uuid4()),'stock_item_id':item,'quantity':'20','service_date':None,'notes':None}
            a=payload(items[0]);b=payload(items[1])
            results=await asyncio.gather(*(store.post(root,json=a) for _ in range(8)))
            assert all(r.status_code==201 for r in results)
            assert sum(r.json()['status']=='REQUESTED' for r in results)==1
            checked(await store.post(root,json={**a,'quantity':'19'}),409)
            checked(await store.post(root,json=b),201)
            raceid=str(uuid.uuid4())
            raced=await asyncio.gather(*(store.post(root,json=payload(item,raceid)) for item in items))
            assert sorted(r.status_code for r in raced)==[201,409]
            for op in (a,b):checked(await owner.post(root+'/'+op['request_id']+'/approve'))
            rid=str(uuid.uuid4());path=root+'/'+a['request_id']+'/receive';body={'receipt_id':rid,'quantity':'3'}
            receipts=await asyncio.gather(*(store.post(path,json=body) for _ in range(8)))
            assert all(r.status_code==201 for r in receipts)
            assert sum(r.json()['already_processed'] is False for r in receipts)==1
            checked(await store.post(path,json={**body,'quantity':'4'}),409)
            collision=str(uuid.uuid4())
            raced=await asyncio.gather(*(store.post(root+'/'+op['request_id']+'/receive',json={'receipt_id':collision,'quantity':'1'}) for op in (a,b)))
            assert sorted(r.status_code for r in raced)==[201,409]
            direct=str(uuid.uuid4())
            checked(await owner.post('/api/v1/kitchen/stock/receipts',json={'movement_id':direct,'stock_item_id':items[0],'quantity':'1','notes':'Collision fixture'}),201)
            checked(await store.post(path,json={'receipt_id':direct,'quantity':'1'}),409)
            assert await db.fetchval('SELECT count(*) FROM kitchen_stock_movements WHERE id=$1',uuid.UUID(collision))==1
            assert await db.fetchval('SELECT count(*) FROM kitchen_procurement_requests WHERE id=$1',uuid.UUID(raceid))==1
            # Run the actual TS journal in separate processes, dropping the response after real commit.
            with tempfile.TemporaryDirectory(prefix='marina-procurement-recovery-') as folder:
                recovery=payload(items[1]);request_op={'kind':'REQUEST',**recovery}
                for op in (request_op,{'kind':'RECEIVE','requestId':recovery['request_id'],'receipt_id':str(uuid.uuid4()),'quantity':'2'}):
                    fixture=Path(folder)/('request.json' if op['kind']=='REQUEST' else 'receive.json')
                    fixture.write_text(json.dumps({'base':base,'cookie':store.headers['Cookie'],'hotel':'ci.local','user':actor['id'],'op':op}));fixture.chmod(0o600)
                    for phase in ('lost-ack','replay'):
                        subprocess.run(['node','scripts/procurement_journal_process_e2e.cjs',str(fixture),phase],check=True)
                        if op['kind']=='REQUEST':
                            assert await db.fetchval('SELECT count(*) FROM kitchen_procurement_requests WHERE id=$1',uuid.UUID(recovery['request_id']))==1
                        else:
                            quantity=await db.fetchval('SELECT "receivedQuantity" FROM kitchen_procurement_requests WHERE id=$1',uuid.UUID(recovery['request_id']))
                            assert quantity==Decimal('2')
                            assert await db.fetchval('SELECT count(*) FROM kitchen_stock_movements WHERE id=$1',uuid.UUID(op['receipt_id']))==1
                    if op['kind']=='REQUEST':checked(await owner.post(root+'/'+recovery['request_id']+'/approve'))
            # Canonical readback shared with Web, plus exact PostgreSQL movement totals.
            stock=checked(await store.get('/api/v1/kitchen/stock'))
            assert sum(Decimal(x['balance']) for x in stock['items'] if x['id'] in items)==Decimal('7')
            assert await db.fetchval('SELECT count(*) FROM payments')==payments
            print('PROCUREMENT RECOVERY POSTGRES PASS: same-ID concurrent requests/receipts, changed item/request 409 not 500, direct-receipt collision; actual mobile TS journal lost ack -> new process -> identical replay; exact stock +7, no Payment')
    finally:await db.close()

if __name__=='__main__':asyncio.run(main())
