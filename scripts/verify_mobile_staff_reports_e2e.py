"""Disposable PostgreSQL: exact mobile repair DTO -> repair/cleaning/inspection cycle."""
import asyncio
import json
import os
import secrets
import uuid
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
    url=os.environ['DATABASE_URL'].split('?',1)[0]
    base=os.environ.get('CORE_API_URL','http://127.0.0.1:8000')
    if os.environ.get('ALLOW_STAFF_REPORT_TEST_WRITES')!='1' or urlparse(url).hostname not in {'localhost','127.0.0.1'} or urlparse(base).hostname not in {'localhost','127.0.0.1'}:
        raise RuntimeError('Explicit disposable localhost targets required')
    conn=await asyncpg.connect(url)
    password=secrets.token_urlsafe(24);suffix=uuid.uuid4().hex[:12]
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner, httpx.AsyncClient(base_url=base,timeout=30) as tech, httpx.AsyncClient(base_url=base,timeout=30) as other, httpx.AsyncClient(base_url=base,timeout=30) as maid:
            me=await login(owner,os.environ['BOOTSTRAP_OWNER_USERNAME'],os.environ['BOOTSTRAP_OWNER_PASSWORD'])
            pid=await conn.fetchval('SELECT id FROM properties WHERE code=$1',me['property_code'])
            rt=await conn.fetchval('SELECT id FROM room_types WHERE "propertyId"=$1 LIMIT 1',pid);assert rt
            room=uuid.uuid4()
            await conn.execute('''INSERT INTO rooms (id,"propertyId","roomTypeId",code,name,"operationalState","createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,'Synthetic repair room','CLEAN',now(),now())''',room,pid,rt,'REPORT-'+suffix)
            actors={}
            for label,role,client in [('tech','TECHNICIAN',tech),('other','TECHNICIAN',other),('maid','MAID',maid)]:
                username='ci-report-'+label+'-'+suffix
                created=checked(await owner.post('/api/v1/admin/staff',json={'username':username,'display_name':'Synthetic '+label,'password':password,'role':role}),201)
                actor=await login(client,username,password);assert actor['role']==role
                actors[label]=actor['id'];assert created['id']==actor['id']
            payments=await conn.fetchval('SELECT count(*) FROM payments')
            tasks=[]
            for label in ('tech','other'):
                result=checked(await owner.post('/api/v1/ops/tasks',json={'type':'MAINTENANCE','room_id':str(room),'title':'Synthetic repair '+label,'assigned_to_id':actors[label]}),201)
                tasks.append(result['id'])
            async def state():return await conn.fetchval('SELECT "operationalState"::text FROM rooms WHERE id=$1',room)
            assert await state()=='TECH_BLOCK'
            report={'summary':'  Valve replaced and checked  ','checklist':[],'evidence_urls':[]}
            path='/api/v1/ops/tasks/'+tasks[0]
            checked(await tech.post(path+'/claim'))
            checked(await other.post(path+'/complete-report',json=report),403)
            checked(await tech.post(path+'/complete-report',json={**report,'summary':'   '}),422)
            checked(await tech.patch('/api/v1/ops/rooms/'+str(room)+'/state',json={'state':'CLEAN'}),403)
            first=checked(await tech.post(path+'/complete-report',json=report))
            assert first['report_recorded'] is True and first['status']=='DONE' and first['room_state']=='TECH_BLOCK'
            assert await state()=='TECH_BLOCK'
            checked(await tech.post(path+'/complete-report',json=report),409)
            audits=await conn.fetch('''SELECT "afterJson" FROM audit_logs WHERE "propertyId"=$1 AND action='COMPLETE_WITH_REPORT' AND "resourceId"=$2''',pid,tasks[0])
            assert len(audits)==1
            audit=json.loads(audits[0]['afterJson']) if isinstance(audits[0]['afterJson'],str) else audits[0]['afterJson']
            assert audit['report']['summary']=='Valve replaced and checked'
            path2='/api/v1/ops/tasks/'+tasks[1]
            checked(await other.post(path2+'/claim'))
            last=checked(await other.post(path2+'/complete-report',json={'summary':'Second repair finished','checklist':[],'evidence_urls':[]}))
            assert last['status']=='DONE' and last['room_state']=='DIRTY' and last['housekeeping_task_id']
            hk=last['housekeeping_task_id'];assert await state()=='DIRTY'
            # API readback used by both Staff Web and Mobile observes the same rows.
            owner_tasks=checked(await owner.get('/api/v1/ops/tasks',params={'limit':300}))['items']
            assert next(t for t in owner_tasks if t['id']==hk)['status']=='OPEN'
            hkpath='/api/v1/ops/tasks/'+hk
            checked(await maid.post(hkpath+'/claim'))
            codes=['BED_LINEN','BATHROOM','SURFACES','AMENITIES','FINAL_CHECK']
            cleaning={'summary':'Cleaned after repairs','checklist':[{'code':c,'label':c,'done':True} for c in codes],'evidence_urls':[]}
            invalid={**cleaning,'checklist':[{'code':codes[0],'label':codes[0],'done':False}]}
            checked(await maid.post(hkpath+'/complete-report',json=invalid),422)
            cleaned=checked(await maid.post(hkpath+'/complete-report',json=cleaning))
            assert cleaned['status']=='IN_INSPECTION' and await state()=='IN_INSPECTION'
            checked(await maid.patch(hkpath+'/status',json={'status':'DONE'}),403)
            checked(await owner.patch(hkpath+'/status',json={'status':'DONE'}))
            assert await state()=='CLEAN'
            assert await conn.fetchval('SELECT count(*) FROM payments')==payments
            print('MOBILE STAFF REPORT POSTGRES PASS: exact mobile repair payload, meaningful audit summary, foreign assignee 403, empty summary 422, duplicate report 409; other repair keeps TECH_BLOCK -> last repair DIRTY + housekeeping -> MAID checklist/inspection -> OWNER CLEAN; no Payment')
    finally:await conn.close()

if __name__=='__main__':asyncio.run(main())
