"""Run once on the fresh synthetic OLD database, before taking the dump."""
import asyncio
import json
from datetime import date, timedelta
from uuid import uuid4
import asyncpg
from argon2 import PasswordHasher

async def seed():
    db = await asyncpg.connect('postgresql://audit@127.0.0.1:55431/marina_fixture')
    async def add(table, **values):
        identity = uuid4()
        values = dict(id=identity, **values)
        columns = ','.join(f'"{c}"' for c in values)
        params = ','.join(f'${i}' for i in range(1, len(values)+1))
        await db.execute(f'INSERT INTO "{table}" ({columns}) VALUES ({params})', *values.values())
        return identity
    async with db.transaction():
        assert not await db.fetchval('select count(*) from properties')
        now = await db.fetchval('select localtimestamp')
        roles = await db.fetch('select unnest(enum_range(null::"StaffRole"))::text role')
        password = PasswordHasher().hash('Synthetic-audit-only-2026!')
        for code in ['ALPHA', 'BETA']:
            pid = await add('properties',code=code,name=f'Synthetic {code}',updatedAt=now)
            for row in roles:
                role=row['role']
                await add('staff_users',propertyId=pid, username=role.lower(),role=role,displayName=role+' '+code,passwordHash=password,updatedAt=now)
            rt = await add('room_types',propertyId=pid,code='STD',name='Standard',capacityAdults=2,updatedAt=now)
            guest = await add('guests',propertyId=pid,firstName='Synthetic',lastName=code,updatedAt=now)
            start=date.today()
            end=start+timedelta(days=2)
            group = await add('booking_groups',propertyId=pid,code=code+'-GROUP',name='Synthetic group',contactName='Fixture',contactPhone='0000000000',contactGuestId=guest,checkIn=start,checkOut=end)
            menu = await add('kitchen_menu_items',propertyId=pid,code='SOUP',category='SOUP',nameRu='Суп',nameKg='Шорпо',nameEn='Soup',priceKgs=125,isDraft=False)
            for n in [1,2]:
                room=await add('rooms',propertyId=pid,roomTypeId=rt,code=str(n),name=f'Room {n}',updatedAt=now)
                res=await add('reservations',propertyId=pid,bookingNumber=f'{code}-{n}',primaryGuestId=guest,checkIn=start,checkOut=end,adults=2,totalKgs=2250,updatedAt=now)
                await add('inventory_blocks',roomId=room,reservationId=res,blockType='RESERVATION',startDate=start,endDate=end,updatedAt=now)
                await add('booking_group_members',groupId=group,reservationId=res,roomId=room)
                await add('payments',reservationId=res,amountKgs=2250 if n==1 else 750,method='CASH',status='RECEIVED',paidAt=now,updatedAt=now)
                order=await add('kitchen_orders',propertyId=pid,reservationId=res,orderNumber=f'{code}-{n}',source='ROOM',status='SERVED',totalKgs=250)
                await add('kitchen_order_items',orderId=order,menuItemId=menu,quantity=2,unitPriceKgs=125,lineTotalKgs=250,status='SERVED')
                charge=await add('guest_folio_charges',propertyId=pid,reservationId=res,guestId=guest,sourceType='KITCHEN_ORDER',sourceId=order,code='DINING',description='Synthetic soup',amountKgs=250,createdByType='STAFF')
                await db.execute('update kitchen_orders set "folioChargeId"=$1 where id=$2',charge,order)
            template=json.load(open('old/services/api/data/site_content_defaults.json'))['ru']
            content={k:{field:f'Synthetic {code} {k} {field}' for field in fields} for k,fields in template.items()}
            await add('site_content_documents',propertyId=pid,locale='ru',draftJson=json.dumps(content),publishedJson=json.dumps(content),publishedVersion=1,publishedAt=now)
    await db.close()
asyncio.run(seed())
