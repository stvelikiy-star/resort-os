import json
import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import require_roles

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
SCOPE = "PUBLIC_SITE"
SUPPORTED_LOCALES = ("ru", "kg", "en")

router = APIRouter(tags=["site-content"])
manager_access = require_roles("OWNER", "MANAGER")


DEFAULT_CONTENT: dict[str, dict[str, Any]] = {
    "ru": {
        "hero": {
            "eyebrow": "Три Короны · Resort & SPA · Чолпон-Ата",
            "title": "Иссык-Куль. Ваш отдых начинается здесь.",
            "copy": "Курорт у самой воды: собственный пляж, 150-метровый пирс, SPA, открытый бассейн и 12 категорий размещения.",
            "primary_cta": "Проверить свободные номера",
            "secondary_cta": "Смотреть номерной фонд",
        },
        "booking": {
            "eyebrow": "Бронирование без лишних шагов",
            "title": "Сначала даты. Потом — лучший вариант.",
            "intro": "Укажите даты и состав гостей. Система покажет свободные категории и стоимость за весь период.",
        },
        "advantages": {
            "eyebrow": "Почему Три Короны",
            "title": "От номера до воды — один маршрут",
            "intro": "Номер, зелёная территория, бассейн, SPA, собственный пляж и пирс складываются в один понятный сценарий отдыха.",
        },
        "groups": {
            "eyebrow": "Групповые заезды",
            "title": "Команды, сборы и корпоративные поездки",
            "copy": "Подберём размещение под состав группы и заранее согласуем питание, трансфер и режим проживания.",
        },
        "contacts": {
            "phone": "+996 558 08 50 02",
            "whatsapp": "+996 558 08 50 08",
            "email": "3koronykg@mail.ru",
            "address": "Иманбай Молдо, Чолпон-Ата 722315, Кыргызстан",
        },
        "seo": {
            "title": "Три Короны — Resort & SPA на Иссык-Куле",
            "description": "Три Короны Resort & SPA в Чолпон-Ате: 84 номера, 12 категорий, собственный пляж, пирс 150 м, SPA и открытый бассейн.",
        },
    },
    "kg": {
        "hero": {
            "eyebrow": "Үч Таажы · Resort & SPA · Чолпон-Ата",
            "title": "Ысык-Көл. Эс алууңуз ушул жерден башталат.",
            "copy": "Көл жээгиндеги эс алуу жайы: өз пляжы, 150 метрлик пирс, SPA, ачык бассейн жана жайгашуунун 12 категориясы.",
            "primary_cta": "Бош номерлерди текшерүү",
            "secondary_cta": "Номерлерди көрүү",
        },
        "booking": {
            "eyebrow": "Жөнөкөй брондоо",
            "title": "Адегенде даталар. Андан кийин — ылайыктуу вариант.",
            "intro": "Келүү-кетүү даталарын жана коноктордун санын көрсөтүңүз. Система бош категорияларды жана мезгилдин баасын көрсөтөт.",
        },
        "advantages": {
            "eyebrow": "Эмне үчүн Үч Таажы",
            "title": "Номерден көлгө чейин — бир маршрут",
            "intro": "Номер, жашыл аймак, бассейн, SPA, өз пляжы жана пирс эс алуунун бирдиктүү сценарийин түзөт.",
        },
        "groups": {
            "eyebrow": "Топтук келүүлөр",
            "title": "Командалар, спорттук жыйындар жана корпоративдик сапарлар",
            "copy": "Топтун курамына жараша жайгашууну тандап, тамактануу, трансфер жана жашоо режимин алдын ала макулдашабыз.",
        },
        "contacts": {
            "phone": "+996 558 08 50 02",
            "whatsapp": "+996 558 08 50 08",
            "email": "3koronykg@mail.ru",
            "address": "Иманбай Молдо, Чолпон-Ата 722315, Кыргызстан",
        },
        "seo": {
            "title": "Үч Таажы — Ысык-Көлдөгү Resort & SPA",
            "description": "Чолпон-Атадагы Үч Таажы Resort & SPA: 84 номер, 12 категория, өз пляжы, 150 м пирс, SPA жана ачык бассейн.",
        },
    },
    "en": {
        "hero": {
            "eyebrow": "Three Crowns · Resort & SPA · Cholpon-Ata",
            "title": "Issyk-Kul. Your stay starts here.",
            "copy": "A lakeside resort with a private beach, a 150-metre pier, SPA, outdoor pool and 12 accommodation categories.",
            "primary_cta": "Check available rooms",
            "secondary_cta": "Explore rooms",
        },
        "booking": {
            "eyebrow": "Straightforward booking",
            "title": "Choose your dates. Then choose your best option.",
            "intro": "Enter your dates and party size. The system will show available categories and the total stay price.",
        },
        "advantages": {
            "eyebrow": "Why Three Crowns",
            "title": "From your room to the lake — one easy route",
            "intro": "Rooms, landscaped grounds, pool, SPA, private beach and pier form one seamless resort experience.",
        },
        "groups": {
            "eyebrow": "Group stays",
            "title": "Teams, training camps and corporate trips",
            "copy": "We help match accommodation to your group and coordinate meals, transfers and the stay schedule in advance.",
        },
        "contacts": {
            "phone": "+996 558 08 50 02",
            "whatsapp": "+996 558 08 50 08",
            "email": "3koronykg@mail.ru",
            "address": "Imanbay Moldo, Cholpon-Ata 722315, Kyrgyzstan",
        },
        "seo": {
            "title": "Three Crowns — Resort & SPA on Issyk-Kul",
            "description": "Three Crowns Resort & SPA in Cholpon-Ata: 84 rooms, 12 categories, private beach, 150 m pier, SPA and outdoor pool.",
        },
    },
}


class SiteContentPayload(BaseModel):
    content: dict[str, Any] = Field(default_factory=dict)


async def get_property_id(conn) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code = $1', PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return value


def validate_locale(locale: str) -> str:
    normalized = locale.lower().strip()
    if normalized not in SUPPORTED_LOCALES:
        raise HTTPException(status_code=404, detail="Unsupported locale")
    return normalized


def default_for(locale: str) -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_CONTENT[locale], ensure_ascii=False))


async def load_row(conn, property_id: uuid.UUID, locale: str):
    return await conn.fetchrow(
        '''
        SELECT id, locale, "draftJson", "publishedJson", version, "publishedVersion",
               "publishedAt", "updatedAt"
        FROM site_content_documents
        WHERE "propertyId"=$1 AND locale=$2 AND scope=$3
        ''',
        property_id,
        locale,
        SCOPE,
    )


@router.get("/api/v1/site/content")
async def public_site_content(request: Request, locale: str = "ru"):
    locale = validate_locale(locale)
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        row = await load_row(conn, property_id, locale)

    if not row or not row["publishedJson"]:
        return {
            "property": PROPERTY_CODE,
            "locale": locale,
            "content": default_for(locale),
            "published_version": 0,
            "published_at": None,
            "source": "DEFAULT",
        }

    return {
        "property": PROPERTY_CODE,
        "locale": locale,
        "content": row["publishedJson"],
        "published_version": row["publishedVersion"],
        "published_at": row["publishedAt"],
        "source": "DATABASE",
    }


@router.get("/api/v1/admin/site/content")
async def admin_site_content(
    request: Request,
    _user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        items = []
        for locale in SUPPORTED_LOCALES:
            row = await load_row(conn, property_id, locale)
            if not row:
                default = default_for(locale)
                items.append({
                    "locale": locale,
                    "draft": default,
                    "published": default,
                    "version": 0,
                    "published_version": 0,
                    "published_at": None,
                    "updated_at": None,
                    "source": "DEFAULT",
                })
                continue
            items.append({
                "locale": locale,
                "draft": row["draftJson"] or default_for(locale),
                "published": row["publishedJson"] or default_for(locale),
                "version": row["version"],
                "published_version": row["publishedVersion"],
                "published_at": row["publishedAt"],
                "updated_at": row["updatedAt"],
                "source": "DATABASE",
            })
    return {"property": PROPERTY_CODE, "items": items}


@router.put("/api/v1/admin/site/content/{locale}/draft")
async def save_site_content_draft(
    locale: str,
    payload: SiteContentPayload,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    locale = validate_locale(locale)
    body = json.dumps(payload.content, ensure_ascii=False)
    document_id = uuid.uuid4()

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            await conn.execute(
                '''
                INSERT INTO site_content_documents (
                    id, "propertyId", locale, scope, "draftJson", "publishedJson",
                    version, "publishedVersion", "updatedByStaffId", "createdAt", "updatedAt"
                ) VALUES ($1,$2,$3,$4,$5::jsonb,'{}'::jsonb,1,0,$6,now(),now())
                ON CONFLICT ("propertyId", locale, scope)
                DO UPDATE SET
                    "draftJson"=EXCLUDED."draftJson",
                    version=site_content_documents.version+1,
                    "updatedByStaffId"=EXCLUDED."updatedByStaffId",
                    "updatedAt"=now()
                ''',
                document_id,
                property_id,
                locale,
                SCOPE,
                body,
                user["id"],
            )
            row = await load_row(conn, property_id, locale)
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                    id,"propertyId","actorType","actorId",action,resource,"resourceId",
                    source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'UPDATE','SiteContentDocument',$4,
                    'ADMIN_CMS','SUCCESS',$5::jsonb,now())
                ''',
                uuid.uuid4(),
                property_id,
                user["id"],
                str(row["id"]),
                json.dumps({"locale": locale, "version": row["version"]}),
            )

    return {"locale": locale, "version": row["version"], "draft": row["draftJson"]}


@router.post("/api/v1/admin/site/content/{locale}/publish")
async def publish_site_content(
    locale: str,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    locale = validate_locale(locale)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            row = await load_row(conn, property_id, locale)
            if not row:
                default = default_for(locale)
                await conn.execute(
                    '''
                    INSERT INTO site_content_documents (
                        id,"propertyId",locale,scope,"draftJson","publishedJson",
                        version,"publishedVersion","publishedAt","updatedByStaffId","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5::jsonb,$5::jsonb,1,1,now(),$6,now(),now())
                    ''',
                    uuid.uuid4(),
                    property_id,
                    locale,
                    SCOPE,
                    json.dumps(default, ensure_ascii=False),
                    user["id"],
                )
            else:
                await conn.execute(
                    '''
                    UPDATE site_content_documents
                    SET "publishedJson"="draftJson",
                        "publishedVersion"=version,
                        "publishedAt"=now(),
                        "updatedByStaffId"=$1,
                        "updatedAt"=now()
                    WHERE id=$2
                    ''',
                    user["id"],
                    row["id"],
                )
            published = await load_row(conn, property_id, locale)
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                    id,"propertyId","actorType","actorId",action,resource,"resourceId",
                    source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'PUBLISH','SiteContentDocument',$4,
                    'ADMIN_CMS','SUCCESS',$5::jsonb,now())
                ''',
                uuid.uuid4(),
                property_id,
                user["id"],
                str(published["id"]),
                json.dumps({"locale": locale, "published_version": published["publishedVersion"]}),
            )

    return {
        "locale": locale,
        "published_version": published["publishedVersion"],
        "published_at": published["publishedAt"],
        "content": published["publishedJson"],
    }
