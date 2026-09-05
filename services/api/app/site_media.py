import hashlib
import uuid
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .site_content import get_property_id

router = APIRouter(tags=["site-media"])
manager_access = require_roles("OWNER", "MANAGER")
MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}

SLOT_LABELS: dict[str, str] = {
    "HERO": "Главный экран",
    "CONFERENCE": "Конференц-зал",
    **{f"GALLERY_{index}": f"Галерея · фото {index}" for index in range(1, 9)},
    **{f"ADVANTAGE_{index}": f"Преимущество · карточка {index}" for index in range(1, 7)},
    **{f"ROOM_{index:02d}": f"Номерной фонд · категория {index:02d}" for index in range(1, 13)},
}


class SlotDraftPatch(BaseModel):
    asset_id: uuid.UUID | None = None
    alt_text: str | None = Field(default=None, max_length=500)


def valid_magic(content_type: str, body: bytes) -> bool:
    if content_type == "image/jpeg":
        return len(body) >= 3 and body[:3] == b"\xff\xd8\xff"
    if content_type == "image/png":
        return len(body) >= 8 and body[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/webp":
        return len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
    return False


def validate_slot(slot: str) -> str:
    normalized = slot.strip().upper()
    if normalized not in SLOT_LABELS:
        raise HTTPException(
            status_code=404,
            detail={"code": "SITE_MEDIA_SLOT_UNKNOWN", "slot": normalized, "allowed": list(SLOT_LABELS)},
        )
    return normalized


def asset_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "filename": row["filename"],
        "mime_type": row["mimeType"],
        "byte_size": row["byteSize"],
        "sha256": row["sha256Hex"],
        "alt_text": row["altText"],
        "is_active": row["isActive"],
        "url": f"/core/api/v1/site/media/{row['id']}",
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
    }


def media_ref(asset_id, filename, mime_type, byte_size, alt_text):
    if asset_id is None:
        return None
    return {
        "asset_id": str(asset_id),
        "filename": filename,
        "mime_type": mime_type,
        "byte_size": byte_size,
        "alt_text": alt_text,
        "url": f"/core/api/v1/site/media/{asset_id}",
    }


def admin_slot_item(row) -> dict[str, Any]:
    return {
        "slot": row["slot"],
        "label": SLOT_LABELS.get(row["slot"], row["slot"]),
        "version": row["version"],
        "published_version": row["publishedVersion"],
        "published_at": row["publishedAt"],
        "dirty": row["version"] != row["publishedVersion"],
        "draft": media_ref(
            row["draftAssetId"], row["draft_filename"], row["draft_mime"], row["draft_bytes"],
            row["draftAltText"] or row["draft_asset_alt"],
        ),
        "published": media_ref(
            row["publishedAssetId"], row["published_filename"], row["published_mime"], row["published_bytes"],
            row["publishedAltText"] or row["published_asset_alt"],
        ),
        "updated_at": row["updatedAt"],
    }


ADMIN_SLOT_SELECT = '''
SELECT s.slot,s."draftAssetId",s."publishedAssetId",s."draftAltText",s."publishedAltText",
       s.version,s."publishedVersion",s."publishedAt",s."updatedAt",
       da.filename AS draft_filename,da."mimeType" AS draft_mime,da."byteSize" AS draft_bytes,da."altText" AS draft_asset_alt,da."isActive" AS draft_active,
       pa.filename AS published_filename,pa."mimeType" AS published_mime,pa."byteSize" AS published_bytes,pa."altText" AS published_asset_alt,pa."isActive" AS published_active
FROM site_media_slots s
LEFT JOIN site_media_assets da ON da.id=s."draftAssetId" AND da."propertyId"=s."propertyId"
LEFT JOIN site_media_assets pa ON pa.id=s."publishedAssetId" AND pa."propertyId"=s."propertyId"
'''


@router.get("/api/v1/admin/site/media")
async def list_media(request: Request, include_archived: bool = False, _user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        rows = await conn.fetch(
            '''SELECT id,filename,"mimeType","byteSize","sha256Hex","altText","isActive","createdAt","updatedAt"
               FROM site_media_assets WHERE "propertyId"=$1 AND ($2::boolean=true OR "isActive"=true)
               ORDER BY "createdAt" DESC LIMIT 500''', property_id, include_archived,
        )
    return {"items": [asset_item(row) for row in rows]}


@router.post("/api/v1/admin/site/media", status_code=status.HTTP_201_CREATED)
async def upload_media(request: Request, user: dict[str, Any] = Depends(manager_access)):
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED:
        raise HTTPException(status_code=415, detail={"code": "SITE_MEDIA_TYPE_NOT_ALLOWED", "allowed": sorted(ALLOWED)})
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "SITE_MEDIA_INVALID_CONTENT_LENGTH"}) from exc
        if declared_length > MAX_BYTES:
            raise HTTPException(status_code=413, detail={"code": "SITE_MEDIA_TOO_LARGE", "max_bytes": MAX_BYTES})
    body = await request.body()
    if not body or len(body) > MAX_BYTES:
        raise HTTPException(status_code=413, detail={"code": "SITE_MEDIA_TOO_LARGE", "max_bytes": MAX_BYTES})
    if not valid_magic(content_type, body):
        raise HTTPException(status_code=422, detail={"code": "SITE_MEDIA_SIGNATURE_MISMATCH"})

    raw_filename = request.headers.get("x-filename") or "image"
    filename = unquote(raw_filename).strip().replace("\x00", "")[:240] or "image"
    alt_text = unquote(request.headers.get("x-alt-text") or "").strip()[:500] or None
    digest = hashlib.sha256(body).hexdigest()

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            existing = await conn.fetchrow(
                '''SELECT id,filename,"mimeType","byteSize","sha256Hex","altText","isActive","createdAt","updatedAt"
                   FROM site_media_assets WHERE "propertyId"=$1 AND "sha256Hex"=$2
                   ORDER BY "createdAt" DESC LIMIT 1 FOR UPDATE''', property_id, digest,
            )
            if existing:
                if not existing["isActive"]:
                    await conn.execute('UPDATE site_media_assets SET "isActive"=true,"updatedAt"=now() WHERE id=$1', existing["id"])
                    existing = await conn.fetchrow(
                        '''SELECT id,filename,"mimeType","byteSize","sha256Hex","altText","isActive","createdAt","updatedAt"
                           FROM site_media_assets WHERE id=$1''', existing["id"],
                    )
                return {"deduplicated": True, "asset": asset_item(existing)}

            asset_id = uuid.uuid4()
            row = await conn.fetchrow(
                '''INSERT INTO site_media_assets (
                     id,"propertyId",filename,"mimeType","byteSize","sha256Hex",content,"altText","isActive","createdById","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,true,$9,now(),now())
                   RETURNING id,filename,"mimeType","byteSize","sha256Hex","altText","isActive","createdAt","updatedAt"''',
                asset_id, property_id, filename, content_type, len(body), digest, body, alt_text, uuid.UUID(user["id"]),
            )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                   ) VALUES ($1,$2,'STAFF',$3,'UPLOAD','SiteMediaAsset',$4,'ADMIN_CMS','SUCCESS',
                     jsonb_build_object('filename',$5::text,'mime_type',$6::text,'byte_size',$7::int,'sha256',$8::text),now())''',
                uuid.uuid4(), property_id, user["id"], str(asset_id), filename, content_type, len(body), digest,
            )
    return {"deduplicated": False, "asset": asset_item(row)}


@router.post("/api/v1/admin/site/media/{asset_id}/archive")
async def archive_media(asset_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            used_slots = await conn.fetch(
                '''SELECT slot FROM site_media_slots
                   WHERE "propertyId"=$1 AND ("draftAssetId"=$2 OR "publishedAssetId"=$2) ORDER BY slot''',
                property_id, asset_id,
            )
            if used_slots:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "SITE_MEDIA_ASSET_IN_USE",
                        "slots": [row["slot"] for row in used_slots],
                        "message": "Сначала замените или очистите изображение в слотах и опубликуйте изменения.",
                    },
                )
            row = await conn.fetchrow(
                '''UPDATE site_media_assets SET "isActive"=false,"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,filename,"mimeType","byteSize","sha256Hex","altText","isActive","createdAt","updatedAt"''',
                asset_id, property_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Media asset not found")
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
                   VALUES ($1,$2,'STAFF',$3,'ARCHIVE','SiteMediaAsset',$4,'ADMIN_CMS','SUCCESS',now())''',
                uuid.uuid4(), property_id, user["id"], str(asset_id),
            )
    return asset_item(row)


@router.get("/api/v1/admin/site/media/slots")
async def admin_media_slots(request: Request, _user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        rows = await conn.fetch(ADMIN_SLOT_SELECT + ' WHERE s."propertyId"=$1 ORDER BY s.slot', property_id)
    assigned = {row["slot"]: admin_slot_item(row) for row in rows}
    return {
        "items": [
            assigned.get(slot) or {
                "slot": slot,
                "label": label,
                "version": 0,
                "published_version": 0,
                "published_at": None,
                "dirty": False,
                "draft": None,
                "published": None,
                "updated_at": None,
            }
            for slot, label in SLOT_LABELS.items()
        ]
    }


@router.put("/api/v1/admin/site/media/slots/{slot}/draft")
async def save_media_slot_draft(
    slot: str,
    payload: SlotDraftPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    slot = validate_slot(slot)
    alt_text = payload.alt_text.strip() if payload.alt_text and payload.alt_text.strip() else None
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            if payload.asset_id is not None:
                asset = await conn.fetchrow(
                    '''SELECT id,"isActive" FROM site_media_assets WHERE id=$1 AND "propertyId"=$2 FOR SHARE''',
                    payload.asset_id, property_id,
                )
                if not asset or not asset["isActive"]:
                    raise HTTPException(status_code=422, detail={"code": "SITE_MEDIA_ACTIVE_ASSET_REQUIRED"})

            await conn.execute(
                '''INSERT INTO site_media_slots (
                     id,"propertyId",slot,"draftAssetId","draftAltText",version,"publishedVersion","updatedById","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,1,0,$6,now(),now())
                   ON CONFLICT ("propertyId",slot) DO UPDATE SET
                     "draftAssetId"=EXCLUDED."draftAssetId","draftAltText"=EXCLUDED."draftAltText",
                     version=site_media_slots.version+1,"updatedById"=EXCLUDED."updatedById","updatedAt"=now()''',
                uuid.uuid4(), property_id, slot, payload.asset_id, alt_text, uuid.UUID(user["id"]),
            )
            row = await conn.fetchrow(ADMIN_SLOT_SELECT + ' WHERE s."propertyId"=$1 AND s.slot=$2', property_id, slot)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'SAVE_DRAFT','SiteMediaSlot',$4,'ADMIN_CMS','SUCCESS',
                     jsonb_build_object('slot',$4::text,'asset_id',$5::text,'version',$6::int),now())''',
                uuid.uuid4(), property_id, user["id"], slot,
                str(payload.asset_id) if payload.asset_id else None, row["version"],
            )
    return admin_slot_item(row)


@router.post("/api/v1/admin/site/media/slots/{slot}/publish")
async def publish_media_slot(slot: str, request: Request, user: dict[str, Any] = Depends(manager_access)):
    slot = validate_slot(slot)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            current = await conn.fetchrow(
                '''SELECT id,"draftAssetId",version FROM site_media_slots
                   WHERE "propertyId"=$1 AND slot=$2 FOR UPDATE''', property_id, slot,
            )
            if not current:
                raise HTTPException(status_code=409, detail={"code": "SITE_MEDIA_SLOT_DRAFT_REQUIRED"})
            if current["draftAssetId"] is not None:
                active = await conn.fetchval(
                    'SELECT "isActive" FROM site_media_assets WHERE id=$1 AND "propertyId"=$2',
                    current["draftAssetId"], property_id,
                )
                if not active:
                    raise HTTPException(status_code=409, detail={"code": "SITE_MEDIA_DRAFT_ASSET_ARCHIVED"})
            await conn.execute(
                '''UPDATE site_media_slots SET
                     "publishedAssetId"="draftAssetId","publishedAltText"="draftAltText",
                     "publishedVersion"=version,"publishedAt"=now(),"updatedById"=$3,"updatedAt"=now()
                   WHERE "propertyId"=$1 AND slot=$2''',
                property_id, slot, uuid.UUID(user["id"]),
            )
            row = await conn.fetchrow(ADMIN_SLOT_SELECT + ' WHERE s."propertyId"=$1 AND s.slot=$2', property_id, slot)
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'PUBLISH','SiteMediaSlot',$4,'ADMIN_CMS','SUCCESS',
                     jsonb_build_object('slot',$4::text,'published_version',$5::int,'asset_id',$6::text),now())''',
                uuid.uuid4(), property_id, user["id"], slot, row["publishedVersion"],
                str(row["publishedAssetId"]) if row["publishedAssetId"] else None,
            )
    return admin_slot_item(row)


@router.get("/api/v1/site/media-config")
async def public_media_config(request: Request):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        rows = await conn.fetch(
            '''SELECT s.slot,s."publishedAssetId",s."publishedAltText",s."publishedAt",
                      a.filename,a."mimeType",a."byteSize",a."altText",a."isActive"
               FROM site_media_slots s
               JOIN site_media_assets a ON a.id=s."publishedAssetId" AND a."propertyId"=s."propertyId"
               WHERE s."propertyId"=$1 AND s."publishedAssetId" IS NOT NULL AND a."isActive"=true
               ORDER BY s.slot''',
            property_id,
        )
    items = [
        {
            "slot": row["slot"],
            "label": SLOT_LABELS.get(row["slot"], row["slot"]),
            "asset_id": str(row["publishedAssetId"]),
            "filename": row["filename"],
            "mime_type": row["mimeType"],
            "byte_size": row["byteSize"],
            "alt_text": row["publishedAltText"] or row["altText"],
            "url": f"/core/api/v1/site/media/{row['publishedAssetId']}",
            "published_at": row["publishedAt"],
        }
        for row in rows
    ]
    return {
        "items": items,
        "slots": {item["slot"]: item for item in items},
        "truth": "Only explicitly published active media slots are exposed to the public site.",
    }


@router.get("/api/v1/site/media/{asset_id}")
async def public_media(asset_id: uuid.UUID, request: Request):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        row = await conn.fetchrow(
            '''SELECT "mimeType","sha256Hex",content FROM site_media_assets
               WHERE id=$1 AND "propertyId"=$2''', asset_id, property_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Media asset not found")
    etag = f'"{row["sha256Hex"]}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=31536000, immutable"})
    return Response(
        content=bytes(row["content"]),
        media_type=row["mimeType"],
        headers={"ETag": etag, "Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"},
    )
