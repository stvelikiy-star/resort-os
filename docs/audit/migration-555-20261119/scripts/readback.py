import asyncio,json,sys
from pathlib import Path
import asyncpg,httpx

async def run(code):
    c=await asyncpg.connect('postgresql://audit@127.0.0.1:55432/marina_fixture')
    with httpx.Client(base_url='http://127.0.0.1:18002',trust_env=False) as api:
        result={}
        login=api.post('/api/v1/auth/login',json={'username':'owner','password':'Synthetic-audit-only-2026!'})
        assert login.json()['property_code']==code
        pid=await c.fetchval('select id from properties where code=$1',code)
        staff=api.get('/api/v1/admin/staff/overview')
        result['staff']={'http':staff.status_code,'matched':sorted(x['id'] for x in staff.json()['staff'])==sorted(str(r[0]) for r in await c.fetch('select id from staff_users where "propertyId"=$1',pid))}
        for rid,gid,total in await c.fetch('select id,"primaryGuestId","totalKgs" from reservations where "propertyId"=$1',pid):
            path='/api/v1/admin/folio/reservations/'+str(rid)
            folio=api.get(path); guest=api.get('/api/v1/admin/guest-crm/'+str(gid)); reservation=api.get('/api/v1/admin/booking/reservations/'+str(rid))
            expected={str(id):amount for id,amount in await c.fetch('select id,"amountKgs" from payments where "reservationId"=$1',rid)}
            f=folio.json()
            result[str(rid)]={'http':[folio.status_code,guest.status_code,reservation.status_code],'guest_id_match':str(gid) in guest.text,'reservation_id_match':str(rid) in reservation.text,'payment_id_amount_match':{x['id']:x['amount_kgs'] for x in f['payments']}==expected,'room_total_match':f['totals']['accommodation_kgs']==total,'folio':f}
        for key in ['health','api/v1/site/content?locale=ru','api/v1/site/content?locale=en','api/v1/site/customer-page?locale=ru']:
            r=api.get('/'+key); result[key]={'status':r.status_code,'content':r.text[:20000]}
        result['logout_status']=api.post('/api/v1/auth/logout').status_code
        result['after_logout']=api.get('/api/v1/auth/me').status_code
        result['relogin']=api.post('/api/v1/auth/login',json={'username':'owner','password':'Synthetic-audit-only-2026!'}).status_code
        Path(f'evidence/readback-{code}.json').write_text(json.dumps(result,ensure_ascii=False,indent=1))
    await c.close()
asyncio.run(run(sys.argv[1]))
