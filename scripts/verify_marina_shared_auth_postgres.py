"""Real PostgreSQL + HTTP acceptance for the isolated shared-auth CI database."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import urlsplit
import uuid

import asyncpg
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth
from app.shared_auth_preview import SharedAuthPreviewBoundary
from app.health import router as health_router


def main():
    dsn = os.environ.get('DATABASE_URL', '').split('?', 1)[0]
    target = urlsplit(dsn)
    assert os.environ.get('MARINA_SHARED_AUTH_CI_CONFIRM') == 'ISOLATED_SHARED_AUTH_CI_ONLY'
    assert target.hostname in {'localhost', '127.0.0.1'} and target.path == '/marina_shared_auth_ci'
    assert auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED and auth.MARINA_TENANT_CONTEXT_ENABLED
    auth.shared_auth_preview_guard()
    ids = {name: uuid.uuid4() for name in ('tenant_a','tenant_b','property_a','property_b','user_a','user_b')}
    passwords = {suffix: secrets.token_urlsafe(24) for suffix in ('a','b')}

    async def seed():
        conn = await asyncpg.connect(dsn)
        try:
            assert await conn.fetchval('SELECT count(*) FROM properties') == 0, 'CI database must be empty'
            async with conn.transaction():
                for suffix in ('a','b'):
                    await conn.execute('''INSERT INTO tenants (id,code,name,status,"updatedAt")
                        VALUES ($1,$2,$3,'ACTIVE',now())''', ids['tenant_'+suffix], 'tenant_'+suffix, 'Synthetic '+suffix)
                    await conn.execute('''INSERT INTO properties (id,code,name,timezone,currency,"updatedAt","tenantId")
                        VALUES ($1,$2,$3,'Asia/Bishkek','KGS',now(),$4)''', ids['property_'+suffix], 'HOTEL_'+suffix.upper(), 'Synthetic '+suffix, ids['tenant_'+suffix])
                    await conn.execute('''INSERT INTO staff_users
                        (id,"propertyId",username,"displayName","passwordHash",role,"isActive","updatedAt")
                        VALUES ($1,$2,'owner',$3,$4,'OWNER',true,now())''', ids['user_'+suffix], ids['property_'+suffix], 'Synthetic owner '+suffix, auth.password_hasher.hash(passwords[suffix]))
        finally:
            await conn.close()
    asyncio.run(seed())

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
        try: yield
        finally: await app.state.db.close()
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(SharedAuthPreviewBoundary)
    app.include_router(auth.router)
    app.include_router(health_router)

    def execute(sql, *args):
        async def run():
            conn = await asyncpg.connect(dsn)
            try: return await conn.execute(sql, *args)
            finally: await conn.close()
        return asyncio.run(run())

    with TestClient(app, base_url='https://shared-auth.test') as client:
        readiness = client.get('/health/ready')
        assert readiness.status_code == 200 and readiness.json()['mode'] == 'shared_auth_preview'
        def login(suffix, password=None, tenant=None):
            return client.post('/api/v1/auth/login', json=dict(username='owner',
                password=password or passwords[suffix], tenant_code=tenant or 'tenant_'+suffix,
                property_code='HOTEL_'+suffix.upper()))
        tokens = {}
        for suffix in ('a','b'):
            response = login(suffix)
            assert response.status_code == 200, response.text
            assert response.json()['property_id'] == str(ids['property_'+suffix])
            assert response.json()['tenant_id'] == str(ids['tenant_'+suffix])
            tokens[suffix] = client.cookies.get(auth.SESSION_COOKIE)
        def me(suffix, token=None):
            return client.get('/api/v1/auth/me', headers={
                'Cookie':auth.SESSION_COOKIE+'='+(token or tokens[suffix]),
                'X-Tenant-Id':str(ids['tenant_b']), 'X-Property-Id':str(ids['property_b']),
                'X-Role':'OWNER'})
        assert me('a').json()['property_code'] == 'HOTEL_A'
        assert me('b').json()['property_code'] == 'HOTEL_B'
        assert login('b', password=passwords['a']).status_code == 401
        assert login('a', tenant='missing').status_code == 401
        parts = tokens['a'].split('.'); parts[2] = str(ids['property_b'])
        assert me('a', token='.'.join(parts)).status_code == 401
        execute("UPDATE tenants SET status='BLOCKED' WHERE id=$1", ids['tenant_a'])
        assert me('a').status_code == 401 and me('b').status_code == 200
        execute("UPDATE tenants SET status='ACTIVE' WHERE id=$1", ids['tenant_a'])
        execute('UPDATE staff_users SET "propertyId"=$1,username=\'moved_owner\' WHERE id=$2', ids['property_b'], ids['user_a'])
        assert me('a').status_code == 401, 'A session must not follow a transferred user'
        execute('UPDATE staff_users SET "isActive"=false WHERE id=$1', ids['user_b'])
        assert me('b').status_code == 401
        execute('UPDATE staff_users SET "isActive"=true WHERE id=$1', ids['user_b'])
        assert client.get('/api/v1/admin/staff').status_code == 503
        assert client.post('/api/v1/reservations',json={}).status_code == 503
        assert client.post('/api/v1/auth/logout',headers={'Cookie':auth.SESSION_COOKIE+'='+tokens['b']}).status_code == 204
        assert me('b').status_code == 401
    print('PASS: PostgreSQL shared login, same usernames, tenant/session isolation, tampering, revocation and closed workspace boundary')


if __name__ == '__main__': main()
