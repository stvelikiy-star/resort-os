import asyncio
import os

import asyncpg


async def main() -> None:
    url = os.environ["DATABASE_URL"].split("?", 1)[0]
    conn = await asyncpg.connect(url)
    try:
        reservations = await conn.fetchval("SELECT count(*)::int FROM reservations")
        stays = await conn.fetchval("SELECT count(*)::int FROM stays")
        if reservations == 0 and stays == 0:
            changed = await conn.execute(
                '''UPDATE rooms
                   SET "operationalState"='CLEAN', "updatedAt"=now()
                   WHERE "operationalState"='UNKNOWN' '''
            )
            print(f"Full-test initial room cleanup: {changed}")
        else:
            print(
                "Full-test room cleanup skipped: "
                f"reservations={reservations}, stays={stays}"
            )
        rooms = await conn.fetchval("SELECT count(*)::int FROM rooms")
        room_types = await conn.fetchval("SELECT count(*)::int FROM room_types")
        clean_rooms = await conn.fetchval(
            '''SELECT count(*)::int FROM rooms WHERE "operationalState"='CLEAN' '''
        )
        print(
            "FULLTEST_STATE "
            f"rooms={rooms} room_types={room_types} reservations={reservations} "
            f"stays={stays} clean_rooms={clean_rooms}"
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
