import json
import os
import re
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
MAX_CONTENT_BYTES = 50_000
MAX_FIELD_CHARS = 5_000

# Public CMS is intentionally narrower than arbitrary marketing copy. These are
# stale commercial rules or amenities that are not yet canonicalized for public
# promotion. Keep this aligned with scripts/public_site_truth_guard.py.
FORBIDDEN_PUBLIC_CONTENT = {
    "fixed 30 percent prepayment": re.compile(
        r"(?:30\s*%[^\n]{0,100}(?:предоплат|prepay|prepayment|алдын\s+ала\s+төл)|(?:предоплат|prepay|prepayment|алдын\s+ала\s+төл)[^\n]{0,100}30\s*%)",
        re.I,
    ),
    "stale two-day unpaid hold": re.compile(
        r"(?:(?:2|two|эки)\s*(?:дн(?:я|ей)?|days?|күн)[^\n]{0,120}(?:брон|reserv|prepay|предоплат|оплат|төл)|(?:брон|reserv|prepay|предоплат|оплат|төл)[^\n]{0,120}(?:2|two|эки)\s*(?:дн(?:я|ей)?|days?|күн))",
        re.I,
    ),
    "fixed first-night prepayment": re.compile(
        r"(?:(?:предоплат|prepay|prepayment|алдын\s+ала\s+төл)[^\n]{0,100}(?:перв[^\n]{0,20}(?:ноч|сут)|first\s+night|биринчи\s+түн)|(?:перв[^\n]{0,20}(?:ноч|сут)|first\s+night|биринчи\s+түн)[^\n]{0,100}(?:предоплат|prepay|prepayment|алдын\s+ала\s+төл))",
        re.I,
    ),
    "uncanonicalized billiards claim": re.compile(r"бильярд|billiards?", re.I),
    "uncanonicalized laundry claim": re.compile(r"прачечн|laundry|кир\s+жуучу", re.I),
    "uncanonicalized sauna claim": re.compile(r"саун|sauna", re.I),
}

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


def _content_strings(content: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for section in content.values():
        if isinstance(section, dict):
            values.extend(value for value in section.values() if isinstance(value, str))
    return values


def validate_public_content(locale: str, content: dict[str, Any]) -> None:
    """Validate schema and public-sales truth before content reaches draft/publish.

    CMS is deliberately structured: top-level sections and fields must already
    exist in the reviewed locale defaults. This prevents the CMS from becoming
    an arbitrary parallel marketing schema and keeps runtime selectors stable.
    """
    template = default_for(locale)
    encoded = json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_CONTENT_BYTES:
        raise HTTPException(
            status_code=422,
            detail={"code": "PUBLIC_CONTENT_TOO_LARGE", "max_bytes": MAX_CONTENT_BYTES},
        )

    for section_name, section in content.items():
        if section_name not in template:
            raise HTTPException(
                status_code=422,
                detail={"code": "PUBLIC_CONTENT_UNKNOWN_SECTION", "section": section_name},
            )
        template_section = template[section_name]
        if not isinstance(template_section, dict) or not isinstance(section, dict):
            raise HTTPException(
                status_code=422,
                detail={"code": "PUBLIC_CONTENT_INVALID_SECTION", "section": section_name},
            )
        for field_name, value in section.items():
            if field_name not in template_section:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "PUBLIC_CONTENT_UNKNOWN_FIELD", "section": section_name, "field": field_name},
                )
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=422,
                    detail={"code": "PUBLIC_CONTENT_FIELD_NOT_TEXT", "section": section_name, "field": field_name},
                )
            if len(value) > MAX_FIELD_CHARS:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "PUBLIC_CONTENT_FIELD_TOO_LONG", "section": section_name, "field": field_name, "max_chars": MAX_FIELD_CHARS},
                )

    combined = "\n".join(_content_strings(content))
    for label, pattern in FORBIDDEN_PUBLIC_CONTENT.items():
        if pattern.search(combined):
            raise HTTPException(
                status_code=422,
                detail={"code": "PUBLIC_CONTENT_TRUTH_VIOLATION", "rule": label, "locale": locale},
            )


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
    validate_public_content(locale, payload.content)
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
                seed_content = default_for(locale)
                validate_public_content(locale, seed_content)
                seed = json.dumps(seed_content, ensure_ascii=False)
                await conn.execute(
                    '''INSERT INTO site_content_documents (
                        id,"propertyId",locale,scope,"draftJson","publishedJson",version,"publishedVersion","publishedAt","updatedByStaffId","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5::jsonb,$5::jsonb,1,1,now(),$6,now(),now())''',
                    uuid.uuid4(), property_id, locale, SCOPE, seed, staff_id,
                )
            else:
                # Revalidate under the publish transaction. This is intentional
                # even though save-draft validates too: publish is the public boundary.
                validate_public_content(locale, row["draftJson"])
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
