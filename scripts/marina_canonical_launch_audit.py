"""Measure release blockers against the canonical application and disposable PG16.

This intentionally returns nonzero when shared operational workspaces do not work.
Never substitute router-only test applications or turn off the canonical boundary.
"""
import asyncio
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

import asyncpg
import httpx
import websockets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'services/api'))
BASELINE = '34d705d2f126a60bd44c2fd17375d97f17dd9025'
SOURCE_PATHS = ('services/api', 'apps/admin', 'apps/staff', 'apps/web', 'packages/database')


def guard():
    dsn = os.environ.get('DATABASE_URL', '').split('?', 1)[0]
    target = urlsplit(dsn)
    if (os.environ.get('MARINA_CANONICAL_AUDIT_CONFIRM') != 'LOCAL_SYNTHETIC_EMPTY_DB_ONLY'
            or target.scheme not in {'postgres', 'postgresql'}
            or target.hostname not in {'localhost', '127.0.0.1'}
            or target.path != '/marina_launch_acceptance_ci'
            or os.environ.get('APP_ENV') != 'staging'
            or os.environ.get('PROPERTY_CODE') != 'MARINA_CANONICAL_AUDIT'
            or os.environ.get('MARINA_SHARED_AUTH_PREVIEW_ENABLED') != 'true'
            or os.environ.get('MARINA_TENANT_CONTEXT_ENABLED') != 'true'):
        raise RuntimeError('Canonical audit requires the explicitly isolated local CI database and shared mode')
    for path in SOURCE_PATHS:
        previous = subprocess.check_output(['git', 'rev-parse', BASELINE+':'+path], cwd=ROOT, text=True).strip()
        current = subprocess.check_output(['git', 'rev-parse', 'HEAD:'+path], cwd=ROOT, text=True).strip()
        if previous != current:
            raise RuntimeError('Audit application tree differs from the reviewed baseline: '+path)
    return dsn


async def seed(dsn):
    from app.auth import password_hasher
    conn = await asyncpg.connect(dsn)
    try:
        version = await conn.fetchval('SHOW server_version_num')
        if not 160000 <= int(version) < 170000:
            raise RuntimeError('Audit requires PostgreSQL 16')
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'_prisma_migrations'")
        for row in tables:
            name = '"'+row['tablename'].replace('"', '""')+'"'
            if await conn.fetchval('SELECT EXISTS (SELECT 1 FROM '+name+' LIMIT 1)'):
                raise RuntimeError('Refusing nonempty audit database')
        roles = await conn.fetch("SELECT enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid WHERE t.typname='StaffRole' ORDER BY enumsortorder")
        fixtures = []
        async with conn.transaction():
            for suffix in ('a','b'):
                tenant, prop, room_type, room = (uuid.uuid4() for _ in range(4))
                password = secrets.token_urlsafe(24)
                password_hash = password_hasher.hash(password)
                await conn.execute('''INSERT INTO tenants (id,code,name,status,"updatedAt")
                    VALUES ($1,$2,$3,'ACTIVE',now())''', tenant, 'audit_tenant_'+suffix, 'Synthetic tenant '+suffix)
                await conn.execute('''INSERT INTO properties
                    (id,code,name,timezone,currency,"tenantId","updatedAt")
                    VALUES ($1,$2,$3,'Asia/Bishkek','KGS',$4,now())''',
                    prop, 'AUDIT_HOTEL_'+suffix.upper(), 'Synthetic hotel '+suffix, tenant)
                await conn.execute('''INSERT INTO room_types
                    (id,"propertyId",code,name,"capacityAdults","updatedAt")
                    VALUES ($1,$2,'STANDARD','Synthetic standard',2,now())''', room_type, prop)
                await conn.execute('''INSERT INTO rooms (id,"propertyId","roomTypeId",code,name,"updatedAt")
                    VALUES ($1,$2,$3,'101','Synthetic room',now())''', room, prop, room_type)
                for role in roles:
                    await conn.execute('''INSERT INTO staff_users
                        (id,"propertyId",username,"displayName","passwordHash",role,"isActive","updatedAt")
                        VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now())''',
                        uuid.uuid4(), prop, 'audit_'+role['enumlabel'].lower(),
                        'Synthetic '+role['enumlabel'], password_hash, role['enumlabel'])
                fixtures.append(dict(suffix=suffix, property_id=str(prop), tenant_id=str(tenant),
                                     property_code='AUDIT_HOTEL_'+suffix.upper(),
                                     tenant_code='audit_tenant_'+suffix, password=password, room_id=str(room)))
        migrations = await conn.fetch("SELECT migration_name,checksum FROM _prisma_migrations WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL ORDER BY migration_name")
        expected = {p.parent.name:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (ROOT/'packages/database/prisma/migrations').glob('*/migration.sql')}
        actual = {r['migration_name']:r['checksum'] for r in migrations}
        if actual != expected:
            raise RuntimeError('Prisma migration ledger/checksums differ from committed SQL')
        return fixtures, [r['enumlabel'] for r in roles], len(migrations)
    finally:
        await conn.close()


async def websocket_result(base, path, token):
    uri = base.replace('http://', 'ws://')+path
    try:
        async with websockets.connect(uri, additional_headers={
                'Cookie':'resort_session='+token, 'Origin':base}, open_timeout=5) as ws:
            frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            return dict(path=path, status='REACHABLE', frame_type=frame.get('type'))
    except websockets.exceptions.InvalidStatus as error:
        return dict(path=path, status='BLOCKED', handshake_http=error.response.status_code)
    except websockets.exceptions.ConnectionClosed as error:
        return dict(path=path, status='BLOCKED', close_code=error.code)
    except Exception as error:
        return dict(path=path, status='ERROR', error_type=type(error).__name__)


def static_inventory():
    from fastapi.routing import APIRoute, APIWebSocketRoute
    from app.app_entry import app
    from app.staff_control import MANAGED_ROLES
    http_routes = []
    ws_routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            http_routes.append(dict(path=route.path, methods=sorted(route.methods), module=route.endpoint.__module__))
        elif isinstance(route, APIWebSocketRoute):
            ws_routes.append(route.path)
    read_paths = sorted({r['path'] for r in http_routes if 'GET' in r['methods']
                         and r['path'].startswith('/api/v1/') and '{' not in r['path']
                         and not r['path'].startswith('/api/v1/auth/')})
    return http_routes, ws_routes, read_paths, MANAGED_ROLES


def measure(base, fixtures, roles, read_paths):
    results = []
    today = date.today()+timedelta(days=3)
    for fixture in fixtures:
        foreign = next(f for f in fixtures if f['property_id'] != fixture['property_id'])
        for role in roles:
            with httpx.Client(base_url=base, timeout=10) as client:
                login = client.post('/api/v1/auth/login', json={
                    'tenant_code':fixture['tenant_code'], 'property_code':fixture['property_code'],
                    'username':'audit_'+role.lower(), 'password':fixture['password']})
                record = dict(property=fixture['property_code'], role=role, login_http=login.status_code)
                if login.status_code != 200:
                    record.update(status='FAIL', reason='Login failed')
                    results.append(record)
                    continue
                me = client.get('/api/v1/auth/me', headers={'X-Property-Id':foreign['property_id'],
                                                         'X-Tenant-Id':foreign['tenant_id']})
                record['identity_verified'] = (me.status_code == 200 and
                    me.json().get('property_id') == fixture['property_id'] and me.json().get('role') == role)
                record['reads'] = []
                for path in read_paths:
                    response = client.get(path)
                    record['reads'].append(dict(path=path,http=response.status_code))
                    if role == 'OWNER' and response.status_code == 503 and 'sample_blocker_detail' not in record:
                        record['sample_blocker_detail'] = response.json().get('detail')
                if role == 'OWNER':
                    token = client.cookies.get('resort_session')
                    with httpx.Client(base_url=base, timeout=10) as outsider:
                        plain_form = outsider.post('/api/v1/auth/login', json={
                            'username':'audit_owner', 'password':fixture['password']})
                        record['ordinary_admin_staff_login_payload_http'] = plain_form.status_code
                        denied = outsider.post('/api/v1/auth/login', json={
                            'tenant_code':foreign['tenant_code'], 'property_code':foreign['property_code'],
                            'username':'audit_owner', 'password':fixture['password']})
                        record['cross_hotel_password_http'] = denied.status_code
                        pieces = token.split('.')
                        pieces[2] = foreign['property_id']
                        denied = outsider.get('/api/v1/auth/me', headers={
                            'Cookie':'resort_session='+'.'.join(pieces)})
                        record['tampered_session_http'] = denied.status_code
                    record['websockets'] = [asyncio.run(websocket_result(base, path, token))
                                           for path in ('/ws/pms/grid','/ws/dining/ready')]
                    payload = dict(room_id=fixture['room_id'],check_in=str(today),
                                   check_out=str(today+timedelta(days=2)), adults=2, children=0)
                    writes = [
                        ('/api/v1/admin/pms/reservations/new/preview',payload),
                        ('/api/v1/admin/pms/holds',dict(room_id=fixture['room_id'],check_in=str(today),
                            check_out=str(today+timedelta(days=2)),guest_name='Synthetic Audit Guest',guest_phone='+996000000000')),
                        ('/api/v1/admin/staff',dict(username='audit_new_manager', display_name='Synthetic manager',
                            password=secrets.token_urlsafe(24),role='MANAGER')),
                    ]
                    record['writes'] = [dict(path=path,http=client.post(path,json=body).status_code) for path,body in writes]
                record['status'] = ('FAIL' if not record['identity_verified'] else
                    'BLOCKED' if any(r['http']==503 for r in record['reads']) else 'NEEDS_BUSINESS_ACCEPTANCE')
                results.append(record)
    return results


def main():
    output = Path(os.environ.get('MARINA_CANONICAL_AUDIT_OUTPUT', '/tmp/marina-canonical-launch-audit.json'))
    output.parent.mkdir(parents=True,exist_ok=True)
    report = dict(status='ERROR', release_ready=False, baseline=BASELINE,
                  entrypoint='app.app_entry:app', canonical_boundary_modified=False,
                  execution='GITHUB_CI_DISPOSABLE_POSTGRESQL16_NOT_UBUNTU_TARGET')
    process = None
    try:
        dsn = guard()
        fixtures, roles, migration_count = asyncio.run(seed(dsn))
        http_routes, ws_routes, read_paths, managed_roles = static_inventory()
        report.update(migration_count=migration_count, migration_checksums_match=True,
                      database_roles=roles, owner_assignable_roles=managed_roles,
                      http_route_count=len(http_routes), websocket_routes=ws_routes,
                      read_entry_count=len(read_paths), route_inventory=http_routes)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        base = 'http://127.0.0.1:'+str(port)
        with output.with_suffix('.server.log').open('w') as server_log:
            process = subprocess.Popen([sys.executable,'-m','uvicorn','app.app_entry:app','--app-dir','services/api',
                '--host','127.0.0.1','--port',str(port)], cwd=ROOT, stdout=server_log, stderr=server_log)
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    raise RuntimeError('Canonical server exited before readiness')
                try:
                    ready=httpx.get(base+'/health/ready',timeout=1)
                    if ready.status_code==200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError('Canonical server readiness timed out')
            report['readiness']=ready.json()
            report['actors']=measure(base,fixtures,roles,read_paths)
        blocked=sum(r['http']==503 for actor in report['actors'] for r in actor.get('reads',[]))
        identity_failures=sum(not actor.get('identity_verified',False) for actor in report['actors'])
        report.update(status='FAIL' if identity_failures else 'BLOCKED' if blocked else 'INCOMPLETE',
                      blocked_read_requests=blocked,
                      blocked_write_requests=sum(r['http']==503 for actor in report['actors'] for r in actor.get('writes',[])),
                      blocked_socket_connections=sum(r['status']=='BLOCKED' for actor in report['actors'] for r in actor.get('websockets',[])),
                      business_lifecycle_executed=False,
                      identity_failures=identity_failures,
                      remaining_acceptance=['Shared operational business lifecycle','Onboarding through the shared platform',
                          'Live WhatsApp/AI and official OTA/acquiring','Target Ubuntu, HTTPS, real backup restore and restart'])
    except Exception as error:
        report.update(status='ERROR', error_type=type(error).__name__, error=str(error))
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('MARINA_CANONICAL_AUDIT_JSON='+json.dumps(report,ensure_ascii=False,separators=(',',':')))
    print('CANONICAL_LAUNCH_ACCEPTANCE='+report['status']+'; release_ready=false')
    return 1 if report['status'] in {'BLOCKED','FAIL'} else 2


if __name__=='__main__':
    raise SystemExit(main())
