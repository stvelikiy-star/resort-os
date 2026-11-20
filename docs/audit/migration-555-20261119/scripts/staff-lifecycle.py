from pathlib import Path
import asyncio,json
from datetime import date,timedelta
import asyncpg,httpx
async def run():
    db=await asyncpg.connect('postgresql://audit@127.0.0.1:55432/marina_fixture')
    pid=await db.fetchval("select id from properties where code='ALPHA'")
    agent=await db.fetchval('''insert into booking_agents(id,"propertyId",name,"updatedAt") values(gen_random_uuid(),$1,'Synthetic Agency',now()) returning id''',pid)
    await db.execute('''update reservations set "agentId"=$1 where "bookingNumber"='ALPHA-1' ''',agent)
    out={}
    base='http://127.0.0.1:18002'
    with httpx.Client(base_url=base,trust_env=False) as owner,httpx.Client(base_url=base,trust_env=False) as client:
        def login(c,name):
            return c.post('/api/v1/auth/login',json={'username':name,'password':'Synthetic-audit-only-2026!'})
        login(owner,'owner').raise_for_status()
        agent_user=login(client,'agent').json()['id']
        bind=owner.patch('/api/v1/admin/staff/'+agent_user,json={'booking_agent_id':str(agent)})
        out['agent_owner_binding']=bind.status_code
        login(client,'agent').raise_for_status()
        r=client.get('/api/v1/pms/grid',params={'start':str(date.today()),'end':str(date.today()+timedelta(days=2))})
        out['agent_grid']={'http':r.status_code,'own_booking':'ALPHA-1' in r.text,'other_booking':'ALPHA-2' in r.text,'other_property':'BETA' in r.text}
        login(client,'maid').raise_for_status()
        staff=client.get('/api/v1/auth/me').json()['id']
        out['owner_disable']=owner.patch('/api/v1/admin/staff/'+staff,json={'active':False}).status_code
        out['existing_session_after_disable']=client.get('/api/v1/auth/me').status_code
        out['login_after_disable']=login(client,'maid').status_code
        out['owner_reactivate']=owner.patch('/api/v1/admin/staff/'+staff,json={'active':True}).status_code
        out['login_after_reactivate']=login(client,'maid').status_code
        room=await db.fetchval('select id from rooms where "propertyId"=$1 order by code limit 1',pid)
        issue=owner.post(f'/api/v1/admin/guest-os/room-qrs/{room}/issue')
        out['qr_issue_http']=issue.status_code
        if issue.is_success:
            from urllib.parse import urlsplit
            issued=issue.json()
            out['qr_generated_host']=urlsplit(issued['public_url']).hostname
            guest=client.get('/api/v1/guest-os/rooms/'+issued['token'])
            out['qr_property']=guest.json().get('property');out['qr_http']=guest.status_code
    Path('evidence/staff-lifecycle.json').write_text(json.dumps(out,indent=1,ensure_ascii=False))
    await db.close()
asyncio.run(run())
