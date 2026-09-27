import asyncio
import os
import uuid
from datetime import date

import asyncpg

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "MARINA_TEST")
PROPERTY_NAME = os.environ.get("MARINA_PROPERTY_NAME", "MARINA SMART TEST HOTEL")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "MARINA_DIRECT")


def database_url() -> str:
    return os.environ["DATABASE_URL"].replace("?schema=public", "")


async def main() -> None:
    conn = await asyncpg.connect(database_url())
    try:
        async with conn.transaction():
            property_id = await conn.fetchval(
                '''
                INSERT INTO properties (id,code,name,timezone,currency,"createdAt","updatedAt")
                VALUES ($1,$2,$3,'Asia/Bishkek','KGS',now(),now())
                ON CONFLICT (code) DO UPDATE SET
                  name=CASE
                    WHEN properties.name IN ('Три Короны','Three Crowns','MARINA SMART TEST HOTEL')
                    THEN EXCLUDED.name ELSE properties.name
                  END,
                  "updatedAt"=now()
                RETURNING id
                ''',
                uuid.uuid4(), PROPERTY_CODE, PROPERTY_NAME,
            )

            plan_id = await conn.fetchval(
                '''
                INSERT INTO rate_plans (id,"propertyId",code,name,currency,"createdAt","updatedAt")
                VALUES ($1,$2,$3,'MARINA SMART Demo Rate','KGS',now(),now())
                ON CONFLICT ("propertyId",code) DO UPDATE SET "updatedAt"=now()
                RETURNING id
                ''',
                uuid.uuid4(), property_id, RATE_PLAN_CODE,
            )

            room_count = int(await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', property_id))
            type_count = int(await conn.fetchval('SELECT count(*) FROM room_types WHERE "propertyId"=$1', property_id))

            if room_count == 0 and type_count == 0:
                today = date.today()
                valid_from = date(today.year, 1, 1)
                valid_to = date(today.year + 1, 12, 31)
                categories = [
                    ("STANDARD", "Стандарт", 2, 1, "18–24 м²", 3000, 100),
                    ("COMFORT", "Комфорт", 2, 2, "24–32 м²", 4500, 200),
                    ("SUITE", "Люкс", 4, 2, "35–50 м²", 7000, 300),
                ]
                for type_code, type_name, adults, children, area, price, base in categories:
                    room_type_id = uuid.uuid4()
                    await conn.execute(
                        '''
                        INSERT INTO room_types (
                          id,"propertyId",code,name,"capacityAdults","capacityChildren","areaLabel","createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,$4,$5,$6,$7,now(),now())
                        ''',
                        room_type_id, property_id, type_code, type_name, adults, children, area,
                    )
                    await conn.execute(
                        '''
                        INSERT INTO rate_periods (
                          id,"ratePlanId","roomTypeId",label,"validFrom","validTo","priceKgs",
                          "mealIncluded","saleStatus","createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,'Базовый тестовый тариф',$4,$5,$6,'NONE','OPEN',now(),now())
                        ''',
                        uuid.uuid4(), plan_id, room_type_id, valid_from, valid_to, price,
                    )
                    for offset in range(1, 5):
                        code = str(base + offset)
                        await conn.execute(
                            '''
                            INSERT INTO rooms (
                              id,"propertyId","roomTypeId",code,name,"floorLabel","bedConfiguration",
                              "areaLabel","operationalState","createdAt","updatedAt"
                            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'CLEAN',now(),now())
                            ''',
                            uuid.uuid4(), property_id, room_type_id, code, f"Номер {code}",
                            str(base // 100), "1 двуспальная / трансформируемая", area,
                        )
                room_count = 12
                type_count = 3
                print("MARINA bootstrap: created compact demo inventory 12 rooms / 3 categories")
            else:
                print(f"MARINA bootstrap: preserving existing inventory rooms={room_count} room_types={type_count}")

        print(f"MARINA bootstrap OK: property={PROPERTY_CODE}, rooms={room_count}, room_types={type_count}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
