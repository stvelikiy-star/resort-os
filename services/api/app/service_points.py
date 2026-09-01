import json
import os
import secrets
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles
from .guest_os import hash_secret, qr_svg

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
PUBLIC_BASE_URL = os.environ.get("SERVICE_POINT_PUBLIC_BASE_URL", os.environ.get("GUEST_OS_PUBLIC_BASE_URL", "https://3korony.com")).rstrip("/")

admin_router = APIRouter(prefix="/api/v1/admin/service-points", tags=["admin-service-points"])
public_router = APIRouter(prefix="/api/v1/service-points", tags=["service-points"])
admin_access = require_roles("OWNER", "MANAGER")

CATEGORIES = {"POOL", "BEACH", "RESTROOM", "CORRIDOR", "DINING", "SAUNA", "OTHER"}
TASK_TYPES = {"HOUSEKEEPING", "MAINTENANCE", "GUEST_REQUEST"}
PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}


class ServicePointOptionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=120)
    task_type: Literal["HOUSEKEEPING", "MAINTENANCE", "GUEST_REQUEST"]
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"


class ServicePointCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=40)
    zone_label: str | None = Field(default=None, max_length=160)
    request_options: list[ServicePointOptionCreate] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_point(self):
        category = self.category.strip().upper()
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
        normalized = [normalize_code(item.code, max_len=40) for item in self.request_options]
        if len(set(normalized)) != len(normalized):
            raise ValueError("request option codes must be unique")
        return self


class PublicServicePointRequest(BaseModel):
    client_request_id: str = Field(min_length=8, max_length=180)
    request_code: str = Field(min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=1200)


def normalize_code(value: str, *, max_len: int) -> str:
    normalized = "".join(ch for ch in value.strip().upper() if ch.isalnum() or ch in {"_", "-"})
    if len(normalized) < 2:
        raise HTTPException(status_code=422, detail={"code": "INVALID_SERVICE_POINT_CODE"})
    return normalized[:max_len]


async def property_id(conn, property_code: str = PROPERTY_CODE) -> uuid.UUID:
    pid = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not pid:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return pid


async def resolve_service_point(conn, raw_token: str, *, lock: bool = False):
    if not (20 <= len(raw_token) <= 256):
        return None
    suffix = " FOR UPDATE OF qr,sp" if lock else ""
    return await conn.fetchrow(
        f'''
        SELECT qr.id AS qr_id,qr."propertyId",qr."servicePointId",qr.status::text AS qr_status,
               qr.label AS qr_label,qr."issuedAt",sp.code,sp.name,sp.category,sp."zoneLabel",sp."isActive"
        FROM service_point_qrs qr
        JOIN service_points sp ON sp.id=qr."servicePointId"
        WHERE qr."tokenHash"=$1 AND qr.status='ACTIVE' AND sp."isActive"=true{suffix}
        ''',
        hash_secret(raw_token),
    )


async def public_point_payload(conn, point_row) -> dict[str, Any]:
    options = await conn.fetch(
        '''
        SELECT code,label,"taskType"::text AS task_type,priority::text AS priority
        FROM service_point_request_options
        WHERE "servicePointId"=$1 AND "isActive"=true
        ORDER BY label,code
        ''',
        point_row["servicePointId"],
    )
    return {
        "qr_valid": True,
        "point": {
            "code": point_row["code"],
            "name": point_row["name"],
            "category": point_row["category"],
            "zone_label": point_row["zoneLabel"],
        },
        "request_options": [
            {"code": row["code"], "label": row["label"]}
            for row in options
        ],
        "privacy": "ANONYMOUS_LOCATION_QR_NO_GUEST_DATA",
        "financial_effect": "NONE_AUTOMATIC",
        "room_state_effect": "NONE_AUTOMATIC",
    }


def admin_point_payload(row, options: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "category": row["category"],
        "zone_label": row["zoneLabel"],
        "is_active": bool(row["isActive"]),
        "active_qr_id": str(row["active_qr_id"]) if row.get("active_qr_id") else None,
        "qr_issued_at": row.get("qr_issued_at"),
        "request_options": options or [],
    }


async def issue_qr(conn, *, pid: uuid.UUID, point_id: uuid.UUID, label: str | None = None) -> dict[str, Any]:
    point = await conn.fetchrow(
        '''SELECT id,code,name,"isActive" FROM service_points WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
        point_id,
        pid,
    )
    if not point:
        raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_NOT_FOUND"})
    if not point["isActive"]:
        raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_INACTIVE"})
    active = await conn.fetchval(
        '''SELECT id FROM service_point_qrs WHERE "servicePointId"=$1 AND status='ACTIVE' FOR UPDATE''',
        point_id,
    )
    if active:
        raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_ACTIVE_QR_EXISTS", "qr_id": str(active)})

    raw_token = secrets.token_urlsafe(32)
    qr_id = uuid.uuid4()
    await conn.execute(
        '''
        INSERT INTO service_point_qrs (
          id,"propertyId","servicePointId","tokenHash",status,label,"issuedAt","createdAt","updatedAt"
        ) VALUES ($1,$2,$3,$4,'ACTIVE',$5,now(),now(),now())
        ''',
        qr_id,
        pid,
        point_id,
        hash_secret(raw_token),
        label or point["name"],
    )
    public_url = f"{PUBLIC_BASE_URL}/p/{raw_token}"
    return {
        "qr_id": str(qr_id),
        "service_point_id": str(point_id),
        "service_point_code": point["code"],
        "token": raw_token,
        "public_url": public_url,
        "qr_svg": qr_svg(public_url),
        "display_once": True,
    }


@admin_router.get("")
async def list_service_points(request: Request, user: dict[str, Any] = Depends(admin_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT sp.id,sp.code,sp.name,sp.category,sp."zoneLabel",sp."isActive",
                   qr.id AS active_qr_id,qr."issuedAt" AS qr_issued_at
            FROM service_points sp
            LEFT JOIN service_point_qrs qr ON qr."servicePointId"=sp.id AND qr.status='ACTIVE'
            WHERE sp."propertyId"=$1
            ORDER BY sp.category,sp.name
            ''',
            pid,
        )
        result = []
        for row in rows:
            opts = await conn.fetch(
                '''SELECT code,label,"taskType"::text AS task_type,priority::text AS priority,"isActive" AS is_active
                   FROM service_point_request_options WHERE "servicePointId"=$1 ORDER BY label,code''',
                row["id"],
            )
            result.append(admin_point_payload(row, [dict(item) for item in opts]))
    return {"items": result, "token_visibility": "RAW_TOKEN_IS_RETURNED_ONLY_AT_ISSUE_OR_ROTATE"}


@admin_router.post("", status_code=status.HTTP_201_CREATED)
async def create_service_point(
    payload: ServicePointCreate,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    point_code = normalize_code(payload.code, max_len=60)
    category = payload.category.strip().upper()
    zone = payload.zone_label.strip() if payload.zone_label and payload.zone_label.strip() else None
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            exists = await conn.fetchval(
                'SELECT id FROM service_points WHERE "propertyId"=$1 AND code=$2',
                pid,
                point_code,
            )
            if exists:
                raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_CODE_EXISTS"})
            point_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO service_points (id,"propertyId",code,name,category,"zoneLabel","isActive","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6,true,now(),now())''',
                point_id,
                pid,
                point_code,
                payload.name.strip(),
                category,
                zone,
            )
            for option in payload.request_options:
                option_code = normalize_code(option.code, max_len=40)
                await conn.execute(
                    '''INSERT INTO service_point_request_options (
                         id,"servicePointId",code,label,"taskType",priority,"isActive","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5::"OperationalTaskType",$6::"OperationalTaskPriority",true,now(),now())''',
                    uuid.uuid4(),
                    point_id,
                    option_code,
                    option.label.strip(),
                    option.task_type,
                    option.priority,
                )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                   ) VALUES ($1,$2,'STAFF',$3,'CREATE','ServicePoint',$4,'PMS','SUCCESS',
                     jsonb_build_object('code',$5::text,'category',$6::text,'option_count',$7::int),now())''',
                uuid.uuid4(), pid, user["id"], str(point_id), point_code, category, len(payload.request_options),
            )
    return {"id": str(point_id), "code": point_code, "name": payload.name.strip(), "category": category, "is_active": True}


@admin_router.post("/{point_id}/qr/issue", status_code=status.HTTP_201_CREATED)
async def issue_service_point_qr(
    point_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            result = await issue_qr(conn, pid=pid, point_id=point_id)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'ISSUE_QR','ServicePoint',$4,'PMS','SUCCESS',
                     jsonb_build_object('qr_id',$5::text,'raw_token_persisted',false,'nfc_effect','NONE'),now())''',
                uuid.uuid4(), pid, user["id"], str(point_id), result["qr_id"],
            )
    return result


@admin_router.post("/{point_id}/qr/rotate", status_code=status.HTTP_201_CREATED)
async def rotate_service_point_qr(
    point_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            point = await conn.fetchrow(
                'SELECT id FROM service_points WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                point_id,
                pid,
            )
            if not point:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_NOT_FOUND"})
            revoked = await conn.fetchval(
                '''UPDATE service_point_qrs SET status='REVOKED',"revokedAt"=now(),"updatedAt"=now()
                   WHERE "servicePointId"=$1 AND status='ACTIVE' RETURNING id''',
                point_id,
            )
            result = await issue_qr(conn, pid=pid, point_id=point_id)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'ROTATE_QR','ServicePoint',$4,'PMS','SUCCESS',
                     jsonb_build_object('revoked_qr_id',$5::text,'new_qr_id',$6::text,'raw_token_persisted',false),now())''',
                uuid.uuid4(), pid, user["id"], str(point_id), str(revoked) if revoked else None, result["qr_id"],
            )
    return result


@admin_router.post("/{point_id}/qr/revoke")
async def revoke_service_point_qr(
    point_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(admin_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            exists = await conn.fetchval('SELECT id FROM service_points WHERE id=$1 AND "propertyId"=$2', point_id, pid)
            if not exists:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_NOT_FOUND"})
            revoked = await conn.fetchval(
                '''UPDATE service_point_qrs SET status='REVOKED',"revokedAt"=now(),"updatedAt"=now()
                   WHERE "servicePointId"=$1 AND status='ACTIVE' RETURNING id''',
                point_id,
            )
            if not revoked:
                raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_ACTIVE_QR_NOT_FOUND"})
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'REVOKE_QR','ServicePoint',$4,'PMS','SUCCESS',jsonb_build_object('qr_id',$5::text),now())''',
                uuid.uuid4(), pid, user["id"], str(point_id), str(revoked),
            )
    return {"service_point_id": str(point_id), "qr_id": str(revoked), "status": "REVOKED"}


@public_router.get("/{token}")
async def resolve_public_service_point(token: str, request: Request):
    async with request.app.state.db.acquire() as conn:
        point = await resolve_service_point(conn, token)
        if not point:
            raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_QR_NOT_FOUND"})
        return await public_point_payload(conn, point)


@public_router.post("/{token}/requests", status_code=status.HTTP_201_CREATED)
async def create_public_service_point_request(
    token: str,
    payload: PublicServicePointRequest,
    request: Request,
):
    request_code = normalize_code(payload.request_code, max_len=40)
    description = payload.description.strip() if payload.description and payload.description.strip() else None
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            point = await resolve_service_point(conn, token, lock=True)
            if not point:
                raise HTTPException(status_code=404, detail={"code": "SERVICE_POINT_QR_NOT_FOUND"})
            option = await conn.fetchrow(
                '''SELECT id,code,label,"taskType"::text AS task_type,priority::text AS priority
                   FROM service_point_request_options
                   WHERE "servicePointId"=$1 AND code=$2 AND "isActive"=true''',
                point["servicePointId"],
                request_code,
            )
            if not option:
                raise HTTPException(status_code=422, detail={"code": "SERVICE_POINT_REQUEST_NOT_ALLOWED", "request_code": request_code})

            source = f"SERVICE_POINT_{point['code']}"[:60]
            event_payload = {
                "service_point_id": str(point["servicePointId"]),
                "request_code": request_code,
                "description": description,
            }
            event_json = json.dumps(event_payload, ensure_ascii=False, sort_keys=True)
            existing = await conn.fetchrow(
                '''SELECT "eventType","payloadJson","resultResource","resultResourceId"
                   FROM automation_inbound_events
                   WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3''',
                point["propertyId"], source, payload.client_request_id,
            )
            if existing:
                existing_payload = existing["payloadJson"] if isinstance(existing["payloadJson"], dict) else json.loads(existing["payloadJson"])
                if existing["eventType"] != "SERVICE_POINT_REQUEST" or existing_payload != event_payload:
                    raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_IDEMPOTENCY_PAYLOAD_MISMATCH"})
                if existing["resultResource"] == "OperationalTask" and existing["resultResourceId"]:
                    task = await conn.fetchrow(
                        '''SELECT id,status::text AS status,type::text AS type,priority::text AS priority,title
                           FROM operational_tasks WHERE id=$1::uuid''',
                        existing["resultResourceId"],
                    )
                    return {
                        "idempotent_replay": True,
                        "task_id": str(task["id"]) if task else existing["resultResourceId"],
                        "status": task["status"] if task else None,
                        "type": task["type"] if task else None,
                        "priority": task["priority"] if task else None,
                        "title": task["title"] if task else None,
                        "service_point": {"code": point["code"], "name": point["name"]},
                        "financial_effect": "NONE_AUTOMATIC",
                    }
                raise HTTPException(status_code=409, detail={"code": "SERVICE_POINT_REQUEST_RECONCILIATION_REQUIRED"})

            event_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO automation_inbound_events (
                     id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,'SERVICE_POINT_REQUEST',$5::jsonb,now(),now())''',
                event_id, point["propertyId"], source, payload.client_request_id, event_json,
            )
            task_id = uuid.uuid4()
            title = f"{option['label']} · {point['name']}"
            await conn.execute(
                '''INSERT INTO operational_tasks (
                     id,"propertyId","servicePointId",type,status,priority,title,description,"serviceCode",
                     "createdByType","createdById",source,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4::"OperationalTaskType",'OPEN',$5::"OperationalTaskPriority",$6,$7,$8,
                     'ANONYMOUS',NULL,'SERVICE_POINT_QR',now(),now())''',
                task_id, point["propertyId"], point["servicePointId"], option["task_type"], option["priority"],
                title, description, request_code,
            )
            await conn.execute(
                '''UPDATE automation_inbound_events SET "resultResource"='OperationalTask',"resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''',
                str(task_id), event_id,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                   ) VALUES ($1,$2,'ANONYMOUS',NULL,'CREATE_SERVICE_POINT_REQUEST','OperationalTask',$3,'SERVICE_POINT_QR','SUCCESS',
                     jsonb_build_object('service_point_id',$4::text,'request_code',$5::text,'task_type',$6::text,
                       'priority',$7::text,'guest_data','NONE','financial_effect','NONE_AUTOMATIC','room_state_effect','NONE_AUTOMATIC'),now())''',
                uuid.uuid4(), point["propertyId"], str(task_id), str(point["servicePointId"]), request_code,
                option["task_type"], option["priority"],
            )
    return {
        "idempotent_replay": False,
        "task_id": str(task_id),
        "status": "OPEN",
        "type": option["task_type"],
        "priority": option["priority"],
        "title": title,
        "service_point": {"code": point["code"], "name": point["name"]},
        "privacy": "ANONYMOUS_LOCATION_QR_NO_GUEST_DATA",
        "financial_effect": "NONE_AUTOMATIC",
        "room_state_effect": "NONE_AUTOMATIC",
    }
