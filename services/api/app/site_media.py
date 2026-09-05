import hashlib
import uuid
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from .auth import require_roles
from .site_content import get_property_id

router = APIRouter(tags=["site-media"])
manager_access = require_roles("OWNER", "MANAGER")
MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}


def valid_magic(content_type: str, body: bytes) -> bool:
    if content_type == "image/jpeg":
        return len(body) >= 3 and body[:3] == b"\xff\xd8\xff"
    if content_type == "image/png":
        return len(body) >= 8 and body[:8] == b"\x89PNG\r\n\x1a\n"
    if content_type == "image/webp":
        return len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
    return False


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
    if content_length and int(content_length) > MAX_BYTES:
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
