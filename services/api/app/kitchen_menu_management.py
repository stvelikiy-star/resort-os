import json
import os
import re
import uuid
from typing import Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles
from .kitchen import DRAFT_MENU

router = APIRouter(prefix="/api/v1/kitchen", tags=["kitchen-menu-management"])
manager_access = require_roles("OWNER", "MANAGER")
Category = Literal["BREAKFAST", "SOUP", "SALAD", "MAIN", "SIDE", "DESSERT", "DRINK"]


class MenuCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    category: Category
    name_ru: str = Field(min_length=1, max_length=160)
    name_kg: str | None = Field(default=None, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    price_kgs: int = Field(ge=0, le=100_000)
    is_active: bool = True
    is_draft: bool = True
    sort_order: int = Field(default=0, ge=0, le=100_000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        code = re.sub(r"[^A-Z0-9_]+", "_", value.strip().upper()).strip("_")
        if len(code) < 2:
            raise ValueError("Menu code must contain at least two letters or digits")
        return code


class MenuPatch(BaseModel):
    category: Category | None = None
    name_ru: str | None = Field(default=None, min_length=1, max_length=160)
    name_kg: str | None = Field(default=None, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    price_kgs: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
    is_draft: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)


async def _property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def _item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "category": row["category"],
        "name_ru": row["nameRu"],
        "name_kg": row["nameKg"],
        "name_en": row["nameEn"],
        "price_kgs": row["priceKgs"],
        "is_active": row["isActive"],
        "is_draft": row["isDraft"],
        "sort_order": row["sortOrder"],
    }


async def _audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, item_id: uuid.UUID, before: Any, after: Any) -> None:
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'KitchenMenuItem',$5,'KITCHEN_ADMIN','SUCCESS',$6::jsonb,$7::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, str(item_id),
        json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
    )


@router.post("/menu/bootstrap-draft")
async def bootstrap_draft_menu(request: Request, user: dict[str, Any] = Depends(manager_access)):
    """Test/staging bootstrap only; production must never seed synthetic menu data.

    This route intentionally shadows the historical operational-router endpoint because
    this manager router is mounted first. DINING_STAFF therefore receives 403, while a
    production runtime receives 404 even for OWNER/MANAGER.
    """
    if os.environ.get("APP_ENV", "development").strip().lower() == "production":
        raise HTTPException(status_code=404, detail="Not found")

    created = 0
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            for code, category, ru, kg, en, price, sort_order in DRAFT_MENU:
                result = await conn.execute(
                    '''INSERT INTO kitchen_menu_items (
                         id,"propertyId",code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,true,true,$9,now(),now())
                       ON CONFLICT ("propertyId",code) DO NOTHING''',
                    uuid.uuid4(), pid, code, category, ru, kg, en, price, sort_order,
                )
                created += int(result.endswith("1"))
    return {"created": created, "draft": True, "truth": "TEST_STAGING_BOOTSTRAP_ONLY"}


@router.post("/menu", status_code=status.HTTP_201_CREATED)
async def create_menu_item(payload: MenuCreate, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            item_id = uuid.uuid4()
            try:
                row = await conn.fetchrow(
                    '''INSERT INTO kitchen_menu_items (
                         id,"propertyId",code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,now(),now())
                       RETURNING id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"''',
                    item_id, pid, payload.code, payload.category, payload.name_ru,
                    payload.name_kg or payload.name_ru, payload.name_en or payload.name_ru,
                    payload.price_kgs, payload.is_active, payload.is_draft, payload.sort_order,
                )
            except asyncpg.UniqueViolationError as exc:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_MENU_CODE_EXISTS", "menu_code": payload.code}) from exc
            result = _item(row)
            await _audit(conn, pid, user, "CREATE_MENU_ITEM", item_id, None, result)
    return result


@router.patch("/menu/{item_id}")
async def update_menu_item(item_id: uuid.UUID, payload: MenuPatch, request: Request, user: dict[str, Any] = Depends(manager_access)):
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="No menu changes supplied")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            before_row = await conn.fetchrow(
                '''SELECT id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"
                   FROM kitchen_menu_items WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                item_id, pid,
            )
            if not before_row:
                raise HTTPException(status_code=404, detail="Menu item not found")
            row = await conn.fetchrow(
                '''UPDATE kitchen_menu_items SET
                     category=COALESCE($3,category),"nameRu"=COALESCE($4,"nameRu"),"nameKg"=COALESCE($5,"nameKg"),
                     "nameEn"=COALESCE($6,"nameEn"),"priceKgs"=COALESCE($7,"priceKgs"),"isActive"=COALESCE($8,"isActive"),
                     "isDraft"=COALESCE($9,"isDraft"),"sortOrder"=COALESCE($10,"sortOrder"),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,code,category,"nameRu","nameKg","nameEn","priceKgs","isActive","isDraft","sortOrder"''',
                item_id, pid, payload.category, payload.name_ru, payload.name_kg, payload.name_en,
                payload.price_kgs, payload.is_active, payload.is_draft, payload.sort_order,
            )
            before = _item(before_row)
            after = _item(row)
            await _audit(conn, pid, user, "UPDATE_MENU_ITEM", item_id, before, after)
    return after
