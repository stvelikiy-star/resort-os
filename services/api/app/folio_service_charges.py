import json
import uuid


async def ensure_guest_service_charge(conn, task_id: uuid.UUID, *, actor_type: str, actor_id: str | None) -> uuid.UUID | None:
    await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'folio:guest-service:{task_id}')
    task = await conn.fetchrow(
        '''SELECT t.id,t."propertyId",t."reservationId",t."stayId",t."serviceCode",t.title,t."chargeKgs",t."chargeStatus",
                  t."serviceDate",s."guestId"
           FROM operational_tasks t
           LEFT JOIN stays s ON s.id=t."stayId"
           WHERE t.id=$1 FOR UPDATE''', task_id,
    )
    if not task or not task["reservationId"] or task["chargeKgs"] is None or int(task["chargeKgs"]) <= 0:
        return None
    existing = await conn.fetchval(
        '''SELECT id FROM guest_folio_charges
           WHERE "sourceType"='GUEST_SERVICE' AND "sourceId"=$1 AND status<>'VOID' LIMIT 1''', task_id,
    )
    if existing:
        await conn.execute(
            '''UPDATE operational_tasks SET "chargeStatus"='POSTED',"chargeSource"='FOLIO',"updatedAt"=now() WHERE id=$1''', task_id,
        )
        return existing

    charge_id = uuid.uuid4()
    await conn.execute(
        '''INSERT INTO guest_folio_charges (
             id,"propertyId","reservationId","stayId","guestId","sourceType","sourceId",code,description,"amountKgs",status,
             "serviceDate","createdByType","createdById",metadata,"createdAt","updatedAt"
           ) VALUES ($1,$2,$3,$4,$5,'GUEST_SERVICE',$6,$7,$8,$9,'OPEN',$10,$11,$12,$13::jsonb,now(),now())''',
        charge_id, task["propertyId"], task["reservationId"], task["stayId"], task["guestId"], task_id,
        task["serviceCode"] or "GUEST_SERVICE", task["title"], int(task["chargeKgs"]), task["serviceDate"],
        actor_type, actor_id,
        json.dumps({"task_id": str(task_id), "payment_effect": "NONE"}, ensure_ascii=False),
    )
    await conn.execute(
        '''UPDATE operational_tasks SET "chargeStatus"='POSTED',"chargeSource"='FOLIO',"updatedAt"=now() WHERE id=$1''', task_id,
    )
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,$3,$4,'POST_GUEST_SERVICE_TO_FOLIO','GuestFolioCharge',$5,'FOLIO','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), task["propertyId"], actor_type, actor_id, str(charge_id),
        json.dumps({"task_id": str(task_id), "amount_kgs": int(task["chargeKgs"]), "payment_created": False}, ensure_ascii=False),
    )
    return charge_id


async def void_guest_service_charge(conn, task_id: uuid.UUID, *, actor_type: str, actor_id: str | None, reason: str) -> uuid.UUID | None:
    charge = await conn.fetchrow(
        '''SELECT id,"propertyId",status FROM guest_folio_charges
           WHERE "sourceType"='GUEST_SERVICE' AND "sourceId"=$1 AND status NOT IN ('VOID','WAIVED')
           LIMIT 1 FOR UPDATE''', task_id,
    )
    if not charge:
        return None
    await conn.execute(
        '''UPDATE guest_folio_charges SET status='VOID',
             metadata=COALESCE(metadata,'{}'::jsonb) || jsonb_build_object('void_reason',$2::text,'void_actor',$3::text),
             "updatedAt"=now() WHERE id=$1''', charge["id"], reason, actor_id,
    )
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,$3,$4,'VOID_GUEST_SERVICE_FOLIO_CHARGE','GuestFolioCharge',$5,'FOLIO','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), charge["propertyId"], actor_type, actor_id, str(charge["id"]),
        json.dumps({"task_id": str(task_id), "reason": reason}, ensure_ascii=False),
    )
    return charge["id"]
