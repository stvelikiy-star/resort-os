"""Disposable localhost PostgreSQL: concurrency, lost ack and own API restart."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import httpx


def checked(r, status=200):
    assert r.status_code == status, (status, r.status_code, r.text)
    return r.json()


async def login(client, username, password):
    r = await client.post('/api/v1/auth/login', json={'username': username, 'password': password})
    me = checked(r)
    client.headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in r.cookies.items())
    return me


class LoseReceiptAcknowledgement(httpx.AsyncBaseTransport):
    def __init__(self):
        self.inner = httpx.AsyncHTTPTransport()
        self.lost = False

    async def handle_async_request(self, request):
        response = await self.inner.handle_async_request(request)
        await response.aread()
        if request.method == 'POST' and request.url.path.endswith('/stock/receipts') and response.status_code == 201 and not self.lost:
            self.lost = True
            await response.aclose()
            raise httpx.ReadTimeout('Injected lost acknowledgement AFTER real server commit', request=request)
        return response

    async def aclose(self):
        await self.inner.aclose()


async def main():
    db_url = os.environ['DATABASE_URL'].split('?', 1)[0]
    if os.environ.get('ALLOW_STOCK_RECEIPT_TEST_WRITES') != '1' or urlparse(db_url).hostname not in {'localhost', '127.0.0.1'}:
        raise RuntimeError('Only explicitly opted-in disposable localhost PostgreSQL is permitted')
    db = await asyncpg.connect(db_url)
    process = None
    base = 'http://127.0.0.1:18071'
    with tempfile.TemporaryDirectory(prefix='marina-receipt-') as temporary:
        log_path = Path(temporary) / 'api.log'
        log = log_path.open('w')
        async def start():
            nonlocal process
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.app_entry:app', '--app-dir', 'services/api', '--host', '127.0.0.1', '--port', '18071'], stdout=log, stderr=subprocess.STDOUT)
            async with httpx.AsyncClient(base_url=base, timeout=2) as probe:
                for _ in range(150):
                    if process.poll() is not None:
                        raise RuntimeError('Disposable API failed: ' + log_path.read_text()[-1500:])
                    try:
                        if (await probe.get('/health/ready')).status_code == 200:
                            return
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(0.2)
            raise RuntimeError('Disposable API not ready')
        def stop():
            nonlocal process
            if process is not None:
                process.terminate()
                process.wait(timeout=15)
                process = None
        try:
            await start()
            async with httpx.AsyncClient(base_url=base, timeout=30) as owner, httpx.AsyncClient(base_url=base, timeout=30) as store:
                await login(owner, os.environ['BOOTSTRAP_OWNER_USERNAME'], os.environ['BOOTSTRAP_OWNER_PASSWORD'])
                me = await login(store, os.environ['PROC_STORE_USERNAME'], os.environ['PROC_STORE_PASSWORD'])
                assert me['role'] == 'STORE_STAFF'
                pid = await db.fetchval('SELECT id FROM properties WHERE code=$1', me['property_code'])
                items = []
                for _ in range(2):
                    item = checked(await owner.post('/api/v1/kitchen/stock/items', json={'name': 'RECEIPT-CI-' + uuid.uuid4().hex, 'unit': 'KG', 'cost_per_unit_kgs': '2.5', 'is_sample': False}), 201)
                    items.append(item['id'])
                payments = await db.fetchval('SELECT count(*) FROM payments')
                path = '/api/v1/kitchen/stock/receipts'
                payload = {'movement_id': str(uuid.uuid4()), 'stock_item_id': items[0], 'quantity': '10', 'notes': 'Concurrent synthetic receipt'}
                results = await asyncio.gather(*(store.post(path, json=payload) for _ in range(8)))
                acknowledgements = [checked(r, 201) for r in results]
                assert sum(not x['already_processed'] for x in acknowledgements) == 1
                assert await db.fetchval('SELECT SUM(quantity) FROM kitchen_stock_movements WHERE id=$1', uuid.UUID(payload['movement_id'])) == Decimal(10)
                assert checked(await store.post(path, json={**payload, 'quantity': '10.000000'}), 201)['already_processed']
                for altered in ({'quantity': '11'}, {'notes': 'Different'}, {'stock_item_id': items[1]}):
                    checked(await store.post(path, json={**payload, **altered}), 409)
                checked(await owner.post(path, json=payload), 409)  # Same ID, different actor.
                checked(await store.post(path, json={'stock_item_id': items[0], 'quantity': '1'}), 422)
                await db.execute('UPDATE kitchen_stock_items SET "costPerUnitKgs"=99 WHERE id=$1', uuid.UUID(items[0]))
                replay = checked(await store.post(path, json=payload), 201)
                assert Decimal(replay['unit_cost_kgs']) == Decimal('2.5')
                # Inject a client read timeout after an actual PostgreSQL commit.
                pending = {**payload, 'movement_id': str(uuid.uuid4()), 'quantity': '3', 'notes': 'Lost ack / restart'}
                journal = Path(temporary) / 'pending.json'
                journal.write_text(json.dumps(pending))
                async with httpx.AsyncClient(base_url=base, timeout=30, transport=LoseReceiptAcknowledgement()) as faulty:
                    faulty.headers['Cookie'] = store.headers['Cookie']
                    try:
                        await faulty.post(path, json=pending)
                        raise AssertionError('Injected timeout did not happen')
                    except httpx.ReadTimeout:
                        pass
                assert await db.fetchval('SELECT count(*) FROM kitchen_stock_movements WHERE id=$1', uuid.UUID(pending['movement_id'])) == 1
                stop()
                await start()
                await login(store, os.environ['PROC_STORE_USERNAME'], os.environ['PROC_STORE_PASSWORD'])
                restored = json.loads(journal.read_text())
                assert checked(await store.post(path, json=restored), 201)['already_processed']
                assert await db.fetchval('SELECT SUM(quantity) FROM kitchen_stock_movements WHERE "stockItemId"=$1', uuid.UUID(items[0])) == Decimal(13)
                # Concurrent same key/different products must not produce PK 500.
                key = str(uuid.uuid4())
                races = await asyncio.gather(*(store.post(path, json={**payload, 'movement_id': key, 'stock_item_id': item, 'quantity': '1'}) for item in items))
                assert sorted(r.status_code for r in races) == [201, 409]
                assert await db.fetchval('SELECT count(*) FROM kitchen_stock_movements WHERE id=$1', uuid.UUID(key)) == 1
                assert await db.fetchval('SELECT count(*) FROM payments') == payments
                Path('/tmp/marina-stock-receipt-fixture.json').write_text(json.dumps({'stock_item_id': items[0], 'store_user_id': me['id']}))
                print('DIRECT RECEIPT POSTGRES PASS: 8 concurrent retries -> one +10; payload/actor conflict 409; immutable original cost; injected timeout after commit + API restart -> same ID replay, balance +13; same key/different items -> 201/409; no Payment')
        finally:
            stop()
            log.close()
            await db.close()


async def verify_browser():
    url=os.environ['DATABASE_URL'].split('?',1)[0]
    if os.environ.get('ALLOW_STOCK_RECEIPT_TEST_WRITES')!='1' or urlparse(url).hostname not in {'localhost','127.0.0.1'}:
        raise RuntimeError('Disposable localhost DB only')
    payload=json.loads(Path('/tmp/marina-stock-receipt-browser-result.json').read_text())
    conn=await asyncpg.connect(url)
    try:
        rows=await conn.fetch('SELECT quantity,kind,"stockItemId" FROM kitchen_stock_movements WHERE id=$1',uuid.UUID(payload['movement_id']))
        assert len(rows)==1 and rows[0]['quantity']==Decimal(7) and rows[0]['kind']=='RECEIPT'
        assert rows[0]['stockItemId']==uuid.UUID(payload['stock_item_id'])
        print('STAFF WEB RECEIPT POSTGRES PASS: browser lost-ack/reload/retry produced exactly one +7 movement')
    finally:await conn.close()

if __name__ == '__main__':
    asyncio.run(verify_browser() if '--verify-browser' in sys.argv else main())
