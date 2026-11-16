"""Disposable canonical API/PostgreSQL: cook draft -> OWNER/MANAGER publication."""
import asyncio
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
    url=os.environ['DATABASE_URL'].split('?',1)[0];base=os.environ.get('CORE_API_URL','http://127.0.0.1:8000')
    if os.environ.get('ALLOW_MOBILE_MENU_TEST_WRITES')!='1' or urlparse(url).hostname not in {'localhost','127.0.0.1'} or urlparse(base).hostname not in {'localhost','127.0.0.1'}:
        raise RuntimeError('Disposable localhost opt-in required')
    conn=await asyncpg.connect(url)
    try:
        async with httpx.AsyncClient(base_url=base,timeout=30) as owner,httpx.AsyncClient(base_url=base,timeout=30) as cook,httpx.AsyncClient(base_url=base,timeout=30) as manager,httpx.AsyncClient(base_url=base,timeout=30) as waiter:
            me=await login(owner,os.environ['BOOTSTRAP_OWNER_USERNAME'],os.environ['BOOTSTRAP_OWNER_PASSWORD'])
            await login(cook,os.environ['KITCHEN_MENU_DINING_USERNAME'],os.environ['KITCHEN_MENU_DINING_PASSWORD'])
            await login(waiter,os.environ['WAITER_SERVE_E2E_USERNAME'],os.environ['WAITER_SERVE_E2E_PASSWORD'])
            pid=await conn.fetchval('SELECT id FROM properties WHERE code=$1',me['property_code'])
            password=secrets.token_urlsafe(24);name='ci-publisher-'+uuid.uuid4().hex[:12]
            checked(await owner.post('/api/v1/admin/staff',json={'username':name,'password':password,'role':'MANAGER','display_name':'Synthetic publisher'}),201)
            await login(manager,name,password)
            payments=await conn.fetchval('SELECT count(*) FROM payments')
            for publisher in (owner,manager):
                draft={'code':'MOB_'+uuid.uuid4().hex[:12].upper(),'category':'MAIN','name_ru':'Синтетическое блюдо','name_kg':'Сыноо тамак','name_en':'Synthetic dish','name_kz':'Сынақ тағам','price_kgs':0,'is_active':False,'is_draft':True,'sort_order':0}
                created=checked(await cook.post('/api/v1/kitchen/menu',json=draft),201);dish=created['id'];path='/api/v1/kitchen/menu/'+dish
                before=checked(await waiter.get('/api/v1/kitchen/menu'))['items'];assert not any(x['id']==dish for x in before)
                payload={'price_kgs':750,'is_draft':False,'is_active':True}  # Exact mobile DTO.
                checked(await cook.patch(path,json=payload),403);checked(await waiter.patch(path,json=payload),403)
                checked(await publisher.patch(path,json={'name_kz':''}))
                checked(await publisher.patch(path,json=payload),409)
                checked(await publisher.patch(path,json={'name_kz':draft['name_kz']}))
                checked(await publisher.patch(path,json={**payload,'price_kgs':100001}),422)
                result=checked(await publisher.patch(path,json=payload));assert result['price_kgs']==750 and result['is_active'] and not result['is_draft']
                checked(await publisher.patch(path,json=payload))  # Idempotent state replacement, not a new item.
                row=await conn.fetchrow('SELECT "priceKgs","isActive","isDraft" FROM kitchen_menu_items WHERE id=$1 AND "propertyId"=$2',uuid.UUID(dish),pid)
                assert row['priceKgs']==750 and row['isActive'] and not row['isDraft']
                after=checked(await waiter.get('/api/v1/kitchen/menu'))['items'];assert next(x for x in after if x['id']==dish)['price_kgs']==750
                production=checked(await cook.get('/api/v1/kitchen/production-menu'))['items'];assert any(x['id']==dish for x in production)
                today=await conn.fetchval('SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE id=$1',pid)
                plan={'service_date':today.isoformat(),'meal_type':'LUNCH','menu_item_id':dish,'planned_quantity':2,'prepared_quantity':0}
                checked(await cook.put('/api/v1/kitchen/production-targets',json=plan))
            assert await conn.fetchval('SELECT count(*) FROM payments')==payments
            print('MOBILE MENU PUBLICATION POSTGRES PASS: COOK draft; OWNER and MANAGER publish exact mobile DTO; COOK/WAITER 403; missing translation 409; invalid price 422; waiter sees price and cook can plan production; repeated PATCH creates no second dish or Payment')
    finally:await conn.close()

if __name__=='__main__':asyncio.run(main())
