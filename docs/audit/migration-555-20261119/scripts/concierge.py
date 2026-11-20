"""Authenticated test guest in a synthetic occupied room after the migration measurement."""
import asyncio,json,sys
from pathlib import Path
import asyncpg,httpx
async def main():
    code = sys.argv[1] if len(sys.argv)>1 else 'ALPHA'
    assert code in ('ALPHA','BETA')
    base='https://127.0.0.1:18002' if code=='BETA' else 'http://127.0.0.1:18002'
    verify='runtime/localhost.crt' if code=='BETA' else True
    db=await asyncpg.connect('postgresql://audit@127.0.0.1:55432/marina_fixture')
    async with db.transaction():
        rid,pid,gid,room=await db.fetchrow('''select r.id,r."propertyId",r."primaryGuestId",b."roomId" from reservations r join inventory_blocks b on b."reservationId"=r.id where r."bookingNumber"=$1 ''',code+'-2')
        await db.execute("update reservations set status='CHECKED_IN' where id=$1",rid)
        stay=await db.fetchval('''insert into stays(id,"propertyId","reservationId","guestId",status,"updatedAt") values(gen_random_uuid(),$1,$2,$3,'ACTIVE',now()) returning id''',pid,rid,gid)
        await db.execute('''insert into room_assignments(id,"propertyId","stayId","roomId","startedAt","updatedAt") values(gen_random_uuid(),$1,$2,$3,now(),now())''',pid,stay,room)
    with httpx.Client(base_url=base,trust_env=False,verify=verify) as owner,httpx.Client(base_url=base,trust_env=False,verify=verify) as guest:
        owner.post('/api/v1/auth/login',json={'username':'owner','password':'Synthetic-audit-only-2026!'}).raise_for_status()
        qr=owner.post(f'/api/v1/admin/guest-os/room-qrs/{room}/issue').json()
        pin=owner.post(f'/api/v1/admin/guest-access/reservations/{rid}/pin').json()
        path='/api/v1/guest-os/rooms/'+qr['token']
        admitted=guest.post(path+'/verify',json={'pin':pin['guest_access_pin']})
        context=guest.get(path)
        Path('evidence/concierge-'+code+'.json').write_text(json.dumps({'pin_http':admitted.status_code,'http':context.status_code,'authenticated':context.json().get('authenticated'),'property':context.json().get('property')},indent=1))
    await db.close()
asyncio.run(main())
