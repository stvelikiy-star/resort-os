import json
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id
from .kitchen import DRAFT_MENU
from .kitchen_recipes import RecipeWrite, ingredient_requirements, read_recipe

router = APIRouter(prefix="/api/v1/kitchen", tags=["kitchen-menu-management"])
manager_access = require_roles("OWNER", "MANAGER")
draft_create_access = require_roles("OWNER", "MANAGER", "COOK")
production_read_access = require_roles("OWNER", "MANAGER", "COOK")
production_write_access = require_roles("MANAGER", "COOK")
Category = Literal["BREAKFAST", "SOUP", "SALAD", "MAIN", "SIDE", "DESSERT", "DRINK"]


class MenuCreate(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    category: Category
    name_ru: str = Field(min_length=1, max_length=160)
    name_kg: str = Field(min_length=1, max_length=160)
    name_kz: str = Field(min_length=1, max_length=160)
    name_en: str = Field(min_length=1, max_length=160)
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
    name_kz: str | None = Field(default=None, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    price_kgs: int | None = Field(default=None, ge=0, le=100_000)
    is_active: bool | None = None
    is_draft: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)


async def _property_id(conn, user: dict[str, Any]) -> uuid.UUID:
    return await trusted_property_id(conn, user)


def _item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "category": row["category"],
        "name_ru": row["nameRu"],
        "name_kg": row["nameKg"],
        "name_kz": row["nameKz"],
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
            pid = await _property_id(conn, user)
            for code, category, ru, kg, kz, en, price, sort_order in DRAFT_MENU:
                result = await conn.execute(
                    '''INSERT INTO kitchen_menu_items (
                         id,"propertyId",code,category,"nameRu","nameKg","nameKz","nameEn","priceKgs","isActive","isDraft","sortOrder","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,true,true,$10,now(),now())
                       ON CONFLICT ("propertyId",code) DO NOTHING''',
                    uuid.uuid4(), pid, code, category, ru, kg, kz, en, price, sort_order,
                )
                created += int(result.endswith("1"))
    return {"created": created, "draft": True, "truth": "TEST_STAGING_BOOTSTRAP_ONLY"}


def validate_menu_create_permissions(payload: MenuCreate, user: dict[str, Any]) -> None:
    """COOK may propose only inactive, zero-price drafts; management publishes."""
    if user["role"] == "COOK" and (
        not payload.is_draft or payload.is_active or payload.price_kgs != 0
    ):
        raise HTTPException(status_code=403, detail="COOK can create only inactive zero-price menu drafts")


@router.post("/menu", status_code=status.HTTP_201_CREATED)
async def create_menu_item(payload: MenuCreate, request: Request, user: dict[str, Any] = Depends(draft_create_access)):
    validate_menu_create_permissions(payload, user)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user)
            item_id = uuid.uuid4()
            try:
                row = await conn.fetchrow(
                    '''INSERT INTO kitchen_menu_items (
                         id,"propertyId",code,category,"nameRu","nameKg","nameKz","nameEn","priceKgs","isActive","isDraft","sortOrder","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,now(),now())
                       RETURNING id,code,category,"nameRu","nameKg","nameKz","nameEn","priceKgs","isActive","isDraft","sortOrder"''',
                    item_id, pid, payload.code, payload.category, payload.name_ru,
                    payload.name_kg, payload.name_kz, payload.name_en,
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
            pid = await _property_id(conn, user)
            before_row = await conn.fetchrow(
                '''SELECT id,code,category,"nameRu","nameKg","nameKz","nameEn","priceKgs","isActive","isDraft","sortOrder"
                   FROM kitchen_menu_items WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                item_id, pid,
            )
            if not before_row:
                raise HTTPException(status_code=404, detail="Menu item not found")
            next_name_kz = payload.name_kz if payload.name_kz is not None else before_row["nameKz"]
            publishing = payload.is_draft is False or payload.is_active is True
            if publishing and not str(next_name_kz or "").strip():
                raise HTTPException(
                    status_code=409,
                    detail={"code": "KITCHEN_MENU_TRANSLATIONS_INCOMPLETE", "missing": ["name_kz"]},
                )
            row = await conn.fetchrow(
                '''UPDATE kitchen_menu_items SET
                     category=COALESCE($3,category),"nameRu"=COALESCE($4,"nameRu"),"nameKg"=COALESCE($5,"nameKg"),
                     "nameKz"=COALESCE($6,"nameKz"),"nameEn"=COALESCE($7,"nameEn"),"priceKgs"=COALESCE($8,"priceKgs"),"isActive"=COALESCE($9,"isActive"),
                     "isDraft"=COALESCE($10,"isDraft"),"sortOrder"=COALESCE($11,"sortOrder"),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,code,category,"nameRu","nameKg","nameKz","nameEn","priceKgs","isActive","isDraft","sortOrder"''',
                item_id, pid, payload.category, payload.name_ru, payload.name_kg, payload.name_kz, payload.name_en,
                payload.price_kgs, payload.is_active, payload.is_draft, payload.sort_order,
            )
            before = _item(before_row)
            after = _item(row)
            await _audit(conn, pid, user, "UPDATE_MENU_ITEM", item_id, before, after)
    return after


# A dated preparation target is neither a guest bill nor a menu stock quantity.
# All queries require a validated property identity; composite FK in zz115
# prevents cross-property references even if a caller bypasses API code.
class ProductionTargetWrite(BaseModel):
    service_date: date
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"]
    menu_item_id: uuid.UUID
    planned_quantity: int = Field(ge=0, le=10000)
    prepared_quantity: int = Field(default=0, ge=0, le=10000)
    notes: str | None = Field(default=None, max_length=500)


def _production_item(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]), "menu_item_id": str(row["menuItemId"]),
        "service_date": row["serviceDate"].isoformat(), "meal_type": row["mealType"],
        "planned_quantity": row["plannedQuantity"],
        "prepared_quantity": row["preparedQuantity"],
        "remaining_quantity": row["plannedQuantity"] - row["preparedQuantity"],
        "notes": row["notes"], "name_ru": row["nameRu"],
        "name_kg": row["nameKg"], "name_en": row["nameEn"],
        "name_kz": row["nameKz"], "updated_at": row["updatedAt"].isoformat(),
    }


@router.get("/production-menu")
async def production_menu(request: Request, user: dict[str, Any] = Depends(production_read_access)):
    # Published menu only: exclude unapproved drafts.
    async with request.app.state.db.acquire() as conn:
        pid = await _property_id(conn, user)
        rows = await conn.fetch(
            '''SELECT id,code,category,"nameRu","nameKg","nameEn","nameKz",recipe
               FROM kitchen_menu_items
               WHERE "propertyId"=$1 AND "isActive"=true AND "isDraft"=false
               ORDER BY "sortOrder",code''', pid,
        )
    return {"items": [
        {"id": str(r["id"]), "code": r["code"], "category": r["category"],
         "name_ru": r["nameRu"], "name_kg": r["nameKg"],
         "name_en": r["nameEn"], "name_kz": r["nameKz"], "recipe": read_recipe(r["recipe"])}
        for r in rows
    ]}


@router.get("/production-targets")
async def production_targets(
    request: Request,
    from_date: date | None = None,
    through_date: date | None = None,
    user: dict[str, Any] = Depends(production_read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await _property_id(conn, user)
        tz_name = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', pid)
        try:
            today = datetime.now(ZoneInfo(tz_name or "Asia/Bishkek")).date()
        except (KeyError, ValueError):
            today = datetime.now(ZoneInfo("Asia/Bishkek")).date()
        start = from_date or today
        end = through_date or (start + timedelta(days=6))
        if end < start or (end - start).days > 31:
            raise HTTPException(status_code=422, detail="Production period must be 1-32 days")
        rows = await conn.fetch(
            '''SELECT t.id,t."menuItemId",t."serviceDate",t."mealType",
                      t."plannedQuantity",t."preparedQuantity",t.notes,t."updatedAt",
                      COALESCE(sp."deductedPortions",0)::int AS deducted_portions,
                      m."nameRu",m."nameKg",m."nameEn",m."nameKz",m.recipe
               FROM kitchen_production_targets t
               JOIN kitchen_menu_items m
                 ON m.id=t."menuItemId" AND m."propertyId"=t."propertyId"
               LEFT JOIN kitchen_stock_production_progress sp
                 ON sp."productionTargetId"=t.id AND sp."propertyId"=t."propertyId"
               WHERE t."propertyId"=$1 AND t."serviceDate" BETWEEN $2 AND $3
               ORDER BY t."serviceDate",t."mealType",m."nameRu"''', pid, start, end,
        )
    requirements = ingredient_requirements(rows)
    prepared_rows = [row for row in rows if row["preparedQuantity"] > 0]
    # Reflect actual explicit stock consumption, not merely the planned recipe need.
    requirements["inventory_deducted"] = bool(prepared_rows) and all(
        row["deducted_portions"] == row["preparedQuantity"] for row in prepared_rows
    )
    return {"from_date": start.isoformat(), "through_date": end.isoformat(),
            "items": [_production_item(r) for r in rows],
            "ingredient_requirements": requirements}


@router.put("/production-targets")
async def upsert_production_target(
    payload: ProductionTargetWrite,
    request: Request,
    user: dict[str, Any] = Depends(production_write_access),
):
    # Idempotent replacement for one meal/dish/day, with audit trail.
    if payload.prepared_quantity > payload.planned_quantity:
        raise HTTPException(status_code=422, detail="Prepared portions exceed plan")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user)
            menu = await conn.fetchrow(
                '''SELECT id FROM kitchen_menu_items
                   WHERE id=$1 AND "propertyId"=$2
                     AND "isActive"=true AND "isDraft"=false
                   FOR SHARE''', payload.menu_item_id, pid,
            )
            if menu is None:
                raise HTTPException(status_code=404, detail="Published menu item not found")
            existing = await conn.fetchrow(
                '''SELECT id,"plannedQuantity","preparedQuantity"
                   FROM kitchen_production_targets
                   WHERE "propertyId"=$1 AND "menuItemId"=$2
                     AND "serviceDate"=$3 AND "mealType"=$4 FOR UPDATE''',
                pid, payload.menu_item_id, payload.service_date, payload.meal_type,
            )
            record_id = existing["id"] if existing else uuid.uuid4()
            row = await conn.fetchrow(
                '''INSERT INTO kitchen_production_targets
                     (id,"propertyId","menuItemId","serviceDate","mealType",
                      "plannedQuantity","preparedQuantity",notes,"updatedById")
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                   ON CONFLICT ("propertyId","menuItemId","serviceDate","mealType")
                   DO UPDATE SET "plannedQuantity"=EXCLUDED."plannedQuantity",
                     "preparedQuantity"=EXCLUDED."preparedQuantity",
                     notes=EXCLUDED.notes,"updatedById"=EXCLUDED."updatedById",
                     "updatedAt"=now()
                   RETURNING id,"plannedQuantity","preparedQuantity"''',
                record_id, pid, payload.menu_item_id, payload.service_date,
                payload.meal_type, payload.planned_quantity,
                payload.prepared_quantity, payload.notes, user["id"],
            )
            await conn.execute(
                '''INSERT INTO audit_logs
                     (id,"propertyId","actorType","actorId",action,resource,"resourceId",
                      source,result,"beforeJson","afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'UPSERT_KITCHEN_PRODUCTION_TARGET',
                           'KitchenProductionTarget',$4,'CHEF_OS','SUCCESS',
                           $5::jsonb,$6::jsonb,now())''',
                uuid.uuid4(), pid, user["id"], str(row["id"]),
                json.dumps(dict(existing) if existing else None, default=str),
                json.dumps({"planned_quantity": row["plannedQuantity"],
                            "prepared_quantity": row["preparedQuantity"],
                            "service_date": payload.service_date.isoformat(),
                            "meal_type": payload.meal_type}, default=str),
            )
    return {"id": str(row["id"]), "service_date": payload.service_date.isoformat(),
            "meal_type": payload.meal_type,
            "planned_quantity": row["plannedQuantity"],
            "prepared_quantity": row["preparedQuantity"],
            "remaining_quantity": row["plannedQuantity"] - row["preparedQuantity"],
            "financial_posting": "NONE_AUTOMATIC"}

@router.get("/menu/{item_id}/recipe")
async def menu_recipe(
    item_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(production_read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await _property_id(conn, user)
        row = await conn.fetchrow(
            'SELECT recipe FROM kitchen_menu_items WHERE id=$1 AND "propertyId"=$2',
            item_id, pid,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Menu item not found")
    return {"menu_item_id": str(item_id), "recipe": read_recipe(row["recipe"])}


@router.put("/menu/{item_id}/recipe")
async def save_menu_recipe(
    item_id: uuid.UUID,
    payload: RecipeWrite,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user)
            row = await conn.fetchrow(
                'SELECT recipe FROM kitchen_menu_items WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                item_id, pid,
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Menu item not found")
            before = read_recipe(row["recipe"])
            version = before["version"] if before else 0
            if payload.expected_version != version:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_RECIPE_CONFLICT"})
            recipe = {
                **payload.model_dump(mode="json", exclude={"expected_version"}),
                "version": version + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await conn.execute(
                'UPDATE kitchen_menu_items SET recipe=$3::jsonb,"updatedAt"=now() '
                'WHERE id=$1 AND "propertyId"=$2',
                item_id, pid, json.dumps(recipe, ensure_ascii=False),
            )
            await _audit(conn, pid, user, "UPDATE_MENU_RECIPE", item_id, before, recipe)
    return {"menu_item_id": str(item_id), "recipe": recipe}
