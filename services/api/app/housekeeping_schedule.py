import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .guest_service_settings import load_settings


async def ensure_due_housekeeping_tasks(conn, property_id: uuid.UUID) -> int:
    """Materialize due housekeeping tasks for active stays, idempotently.

    Owner rule: scheduled housekeeping repeats every configured N days (default 3)
    and includes linen change when enabled. The helper is safe to call from every
    staff/manager task-list read because the partial unique index prevents duplicate
    stay/date tasks and the transaction-local advisory lock serializes concurrent reads.
    """
    await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'housekeeping-schedule:{property_id}')
    settings = await load_settings(conn, property_id)
    interval_days = int(settings["scheduled_housekeeping_interval_days"])
    linen_included = bool(settings["scheduled_linen_change_included"])
    if interval_days < 1:
        return 0

    timezone_name = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', property_id)
    try:
        tz = ZoneInfo(timezone_name or "Asia/Bishkek")
    except Exception:
        tz = ZoneInfo("Asia/Bishkek")
    today = datetime.now(tz).date()

    stays = await conn.fetch(
        '''
        SELECT s.id AS stay_id,s."reservationId" AS reservation_id,s."actualCheckInAt",
               r."checkIn",r."checkOut",ra."roomId" AS room_id,room.code AS room_code
        FROM stays s
        JOIN reservations r ON r.id=s."reservationId"
        JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
        JOIN rooms room ON room.id=ra."roomId"
        WHERE s."propertyId"=$1 AND s.status='ACTIVE'
        ''',
        property_id,
    )

    created = 0
    for stay in stays:
        actual = stay["actualCheckInAt"]
        if actual:
            if actual.tzinfo is None:
                check_in_local = actual.replace(tzinfo=tz).date()
            else:
                check_in_local = actual.astimezone(tz).date()
        else:
            check_in_local = stay["checkIn"]
        checkout: date = stay["checkOut"]
        due = check_in_local + timedelta(days=interval_days)
        while due < checkout and due <= today:
            task_id = uuid.uuid4()
            description = (
                f"Плановая уборка по регламенту каждые {interval_days} дн."
                + (" Включена смена постельного белья." if linen_included else "")
            )
            inserted = await conn.fetchval(
                '''
                INSERT INTO operational_tasks (
                  id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,description,
                  "serviceCode","serviceDate","createdByType","createdById",source,
                  "chargeKgs","chargeStatus","chargeSource","createdAt","updatedAt"
                )
                SELECT $1,$2,$3,$4,$5,'HOUSEKEEPING','OPEN','NORMAL',$6,$7,
                       'SCHEDULED_HOUSEKEEPING',$8,'SYSTEM',NULL,'HOUSEKEEPING_SCHEDULE',
                       NULL,'NONE','INCLUDED_IN_STAY',now(),now()
                WHERE NOT EXISTS (
                  SELECT 1 FROM operational_tasks
                  WHERE "stayId"=$5 AND source='HOUSEKEEPING_SCHEDULE'
                    AND "serviceCode"='SCHEDULED_HOUSEKEEPING' AND "serviceDate"=$8
                )
                RETURNING id
                ''',
                task_id,
                property_id,
                stay["room_id"],
                stay["reservation_id"],
                stay["stay_id"],
                f"Плановая уборка · №{stay['room_code']}",
                description,
                due,
            )
            if inserted:
                created += 1
                await conn.execute(
                    '''UPDATE rooms SET "operationalState"='DIRTY',"updatedAt"=now()
                       WHERE id=$1 AND "operationalState"<>'TECH_BLOCK' ''',
                    stay["room_id"],
                )
                await conn.execute(
                    '''INSERT INTO audit_logs (
                       id,"propertyId","actorType",action,resource,"resourceId",source,result,"afterJson","createdAt"
                       ) VALUES ($1,$2,'SYSTEM','CREATE_SCHEDULED_HOUSEKEEPING','OperationalTask',$3,
                         'HOUSEKEEPING_SCHEDULE','SUCCESS',jsonb_build_object(
                           'stay_id',$4::text,'room_id',$5::text,'service_date',$6::text,
                           'interval_days',$7::int,'linen_change_included',$8::boolean,'financial_effect','INCLUDED_IN_STAY'
                         ),now())''',
                    uuid.uuid4(), property_id, str(task_id), str(stay["stay_id"]), str(stay["room_id"]), str(due), interval_days, linen_included,
                )
            due += timedelta(days=interval_days)
    return created
