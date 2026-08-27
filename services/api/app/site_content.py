import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
SCOPE = "PUBLIC_SITE"
SUPPORTED_LOCALES = ("ru", "kg", "en")
DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "data" / "site_content_defaults.json"

router = APIRouter(tags=["site-content"])
manager_access = require_roles("OWNER", "MANAGER")


class SiteContentPayload(BaseModel):
    content: dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def defaults() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Site content defaults are unavailable") from exc
    if not isinstance(payload, dict) or any(locale not in payload for locale in SUPPORTED_LOCALES):
        raise HTTPException(status_code=503, detail="Site content defaults are invalid")
    return payload


def default_for(locale: str) -> dict[str, Any]:
    return json.loads(json.dumps(defaults()[locale], ensure_ascii=False))


def decode_jsonb(value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else fallback
        except json.JSONDecodeError:
            return fallback
    return fallback


def validate_locale(locale: str) -> str:
    normalized = locale.lower().strip()
    if normalized not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail="Unsupported locale")
    return normalized


async def get_property_id(conn) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return value


async def load_row(conn, property_id: uuid.UUID, locale: str) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        '''
        SELECT id,locale,"draftJson","publishedJson",version,"publishedVersion","publishedAt","updatedAt"
        FROM site_content_documents
        WHERE "propertyId"=$1 AND locale=$2 AND scope=$3
        ''',
        property_id, locale, SCOPE,
    )
    if not row:
        return None
    fallback = default_for(locale)
    return {
        "id": row["id"],
        "locale": row["locale"],
        "draftJson": decode_jsonb(row["draftJson"], fallback),
        "publishedJson": decode_jsonb(row["publishedJson"], {}),
        "version": row["version"],
        "publishedVersion": row["publishedVersion"],
        "publishedAt": row["publishedAt"],
        "updatedAt": row["updatedAt"],
    }


@router.get("/api/v1/site/content")
async def public_site_content(request: Request, locale: str = "ru"):
    locale = validate_locale(locale)
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        row = await load_row(conn, property_id, locale)
    if not row or not row["publishedJson"]:
        return {"property": PROPERTY_CODE, "locale": locale, "content": default_for(locale), "published_version": 0, "published_at": None, "source": "DEFAULT"}
    return {"property": PROPERTY_CODE, "locale": locale, "content": row["publishedJson"], "published_version": row["publishedVersion"], "published_at": row["publishedAt"], "source": "DATABASE"}


@router.get("/api/v1/admin/site/content")
async def admin_site_content(request: Request, _user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        items = []
        for locale in SUPPORTED_LOCALES:
            row = await load_row(conn, property_id, locale)
            if not row:
                default = default_for(locale)
                items.append({"locale": locale, "draft": default, "published": default, "version": 0, "published_version": 0, "published_at": None, "updated_at": None, "source": "DEFAULT"})
            else:
                items.append({"locale": locale, "draft": row["draftJson"], "published": row["publishedJson"] or default_for(locale), "version": row["version"], "published_version": row["publishedVersion"], "published_at": row["publishedAt"], "updated_at": row["updatedAt"], "source": "DATABASE"})
    return {"property": PROPERTY_CODE, "items": items}


@router.put("/api/v1/admin/site/content/{locale}/draft")
async def save_site_content_draft(locale: str, payload: SiteContentPayload, request: Request, user: dict[str, Any] = Depends(manager_access)):
    locale = validate_locale(locale)
    body = json.dumps(payload.content, ensure_ascii=False)
    staff_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            await conn.execute(
                '''
                INSERT INTO site_content_documents (
                    id,"propertyId",locale,scope,"draftJson","publishedJson",version,"publishedVersion","updatedByStaffId","createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5::jsonb,'{}'::jsonb,1,0,$6,now(),now())
                ON CONFLICT ("propertyId",locale,scope) DO UPDATE SET
                    "draftJson"=EXCLUDED."draftJson",version=site_content_documents.version+1,
                    "updatedByStaffId"=EXCLUDED."updatedByStaffId","updatedAt"=now()
                ''',
                uuid.uuid4(), property_id, locale, SCOPE, body, staff_id,
            )
            row = await load_row(conn, property_id, locale)
            await conn.execute(
                '''INSERT INTO audit_logs (
                    id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'UPDATE','SiteContentDocument',$4,'ADMIN_CMS','SUCCESS',$5::jsonb,now())''',
                uuid.uuid4(), property_id, user["id"], str(row["id"]), json.dumps({"locale": locale, "version": row["version"]}),
            )
    return {"locale": locale, "version": row["version"], "draft": row["draftJson"]}


@router.post("/api/v1/admin/site/content/{locale}/publish")
async def publish_site_content(locale: str, request: Request, user: dict[str, Any] = Depends(manager_access)):
    locale = validate_locale(locale)
    staff_id = uuid.UUID(user["id"])
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            row = await load_row(conn, property_id, locale)
            if not row:
                seed = json.dumps(default_for(locale), ensure_ascii=False)
                await conn.execute(
                    '''INSERT INTO site_content_documents (
                        id,"propertyId",locale,scope,"draftJson","publishedJson",version,"publishedVersion","publishedAt","updatedByStaffId","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5::jsonb,$5::jsonb,1,1,now(),$6,now(),now())''',
                    uuid.uuid4(), property_id, locale, SCOPE, seed, staff_id,
                )
            else:
                await conn.execute(
                    '''UPDATE site_content_documents SET "publishedJson"="draftJson","publishedVersion"=version,
                       "publishedAt"=now(),"updatedByStaffId"=$1,"updatedAt"=now() WHERE id=$2''',
                    staff_id, row["id"],
                )
            published = await load_row(conn, property_id, locale)
            await conn.execute(
                '''INSERT INTO audit_logs (
                    id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'PUBLISH','SiteContentDocument',$4,'ADMIN_CMS','SUCCESS',$5::jsonb,now())''',
                uuid.uuid4(), property_id, user["id"], str(published["id"]), json.dumps({"locale": locale, "published_version": published["publishedVersion"]}),
            )
    return {"locale": locale, "published_version": published["publishedVersion"], "published_at": published["publishedAt"], "content": published["publishedJson"]}
