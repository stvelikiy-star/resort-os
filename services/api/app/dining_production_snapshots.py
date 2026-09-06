from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles
from .guest_service_settings import load_settings

router = APIRouter(prefix="/api/v1/dining", tags=["dining-production-snapshots"])
read_access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")
capture_access = require_roles("OWNER", "MANAGER", "DINING_STAFF")
MealType = Literal["BREAKFAST", "LUNCH", "DINNER"]
MEALS: tuple[str, ...] = ("BREAKFAST", "LUNCH", "DINNER")


class ProductionSnapshotCreate(BaseModel):
    service_date: date
    meal_type: MealType
    force_before_cutoff: bool = False
    notes: str | None = Field(default=None, max_length=1000)


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def property_timezone(conn, pid: uuid.UUID) -> ZoneInfo:
    value = await conn.fetchval('SELECT timezone FROM properties WHERE id=$1', pid)
    try:
        return ZoneInfo(value or "Asia/Bishkek")
    except Exception:
        return ZoneInfo("Asia/Bishkek")


def source_fingerprint(rows: list[Any]) -> str:
    payload = [
        {
            "id": str(row["id"]),
            "adult": int(row["adultPortions"]),
            "child": int(row["childPortions"]),
            "updated_at": row["updatedAt"].isoformat(),
        }
        for row in rows
    ]
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def aggregate_rows(rows: list[Any]) -> dict[str, Any]:
    adult = sum(int(row["adultPortions"]) for row in rows)
    child = sum(int(row["childPortions"]) for row in rows)
    return {
        "adult_portions": adult,
        "child_portions": child,
        "total_portions": adult + child,
        "entitlement_count": len(rows),
        "source_fingerprint": source_fingerprint(rows),
        "source_max_updated_at": max((row["updatedAt"] for row in rows), default=None),
    }


async def current_rows(conn, pid: uuid.UUID, service_date: date, meal_type: str) -> list[Any]:
    return list(
        await conn.fetch(
            '''SELECT e.id,e."adultPortions",e."childPortions",e."updatedAt"
               FROM dining_entitlements e
               JOIN stays s ON s.id=e."stayId"
               WHERE e."propertyId"=$1 AND e."serviceDate"=$2 AND e."mealType"=$3
                 AND e.status='ACTIVE' AND s.status IN ('PENDING','ACTIVE')
               ORDER BY e.id''',
            pid,
            service_date,
            meal_type,
        )
    )


async def cutoff_info(conn, pid: uuid.UUID, service_date: date, meal_type: str) -> dict[str, Any]:
    settings = await load_settings(conn, pid)
    tz = await property_timezone(conn, pid)
    now = datetime.now(tz)
    setting_key = {
        "BREAKFAST": "breakfast_start",
        "LUNCH": "lunch_start",
        "DINNER": "dinner_start",
    }[meal_type]
    start_time = settings[setting_key]
    cutoff_minutes = int(settings["meal_order_cutoff_minutes"])
    if start_time is None:
        return {
            "status": "UNCONFIGURED",
            "meal_start": None,
            "cutoff_at": None,
            "cutoff_minutes": cutoff_minutes,
            "now": now,
        }
    meal_at = datetime.combine(service_date, start_time, tzinfo=tz)
    cutoff_at = meal_at - timedelta(minutes=cutoff_minutes)
    return {
        "status": "CUTOFF_REACHED" if now >= cutoff_at else "BEFORE_CUTOFF",
        "meal_start": meal_at,
        "cutoff_at": cutoff_at,
        "cutoff_minutes": cutoff_minutes,
        "now": now,
    }


def snapshot_payload(snapshot: Any | None, current: dict[str, Any], cutoff: dict[str, Any]) -> dict[str, Any]:
    if snapshot is None:
        return {
            "state": "OPEN",
            "cutoff_status": cutoff["status"],
            "meal_start": cutoff["meal_start"],
            "cutoff_at": cutoff["cutoff_at"],
            "cutoff_minutes": cutoff["cutoff_minutes"],
            "captured_at": None,
            "captured_by_id": None,
            "captured_by_name": None,
            "forced": False,
            "reason": None,
            "frozen_adult_portions": None,
            "frozen_child_portions": None,
            "frozen_total_portions": None,
            "frozen_entitlement_count": None,
            "delta_adult_portions": None,
            "delta_child_portions": None,
            "delta_total_portions": None,
            "delta_entitlement_count": None,
            "changed_since_snapshot": False,
        }

    frozen_adult = int(snapshot["adultPortions"])
    frozen_child = int(snapshot["childPortions"])
    frozen_total = frozen_adult + frozen_child
    frozen_count = int(snapshot["entitlementCount"])
    return {
        "state": "FROZEN",
        "cutoff_status": cutoff["status"],
        "meal_start": cutoff["meal_start"],
        "cutoff_at": snapshot["cutoffAt"] or cutoff["cutoff_at"],
        "cutoff_minutes": cutoff["cutoff_minutes"],
        "captured_at": snapshot["capturedAt"],
        "captured_by_id": str(snapshot["capturedById"]) if snapshot["capturedById"] else None,
        "captured_by_name": snapshot["captured_by_name"],
        "forced": bool(snapshot["forced"]),
        "reason": snapshot["reason"],
        "frozen_adult_portions": frozen_adult,
        "frozen_child_portions": frozen_child,
        "frozen_total_portions": frozen_total,
        "frozen_entitlement_count": frozen_count,
        "delta_adult_portions": current["adult_portions"] - frozen_adult,
        "delta_child_portions": current["child_portions"] - frozen_child,
        "delta_total_portions": current["total_portions"] - frozen_total,
        "delta_entitlement_count": current["entitlement_count"] - frozen_count,
        "changed_since_snapshot": current["source_fingerprint"] != snapshot["sourceFingerprint"],
    }


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, resource_id: str, payload: dict[str, Any]) -> None:
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'DiningProductionSnapshot',$5,'CHEF_OS','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(),
        pid,
        user["id"],
        action,
        resource_id,
        json.dumps({**payload, "financial_effect": "NONE", "payment_effect": "NONE"}, ensure_ascii=False, default=str),
    )


@router.get("/production-snapshots")
async def production_snapshots(
    request: Request,
    from_date: date | None = Query(default=None),
    through_date: date | None = Query(default=None),
    user: dict[str, Any] = Depends(read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        tz = await property_timezone(conn, pid)
        local_today = datetime.now(tz).date()
        start = from_date or local_today
        end = through_date or (start + timedelta(days=6))
        if end < start or end - start > timedelta(days=31):
            raise HTTPException(status_code=422, detail="Production snapshot range must be 1-32 days")

        source_rows = await conn.fetch(
            '''SELECT e.id,e."serviceDate",e."mealType",e."adultPortions",e."childPortions",e."updatedAt"
               FROM dining_entitlements e
               JOIN stays s ON s.id=e."stayId"
               WHERE e."propertyId"=$1 AND e."serviceDate" BETWEEN $2 AND $3
                 AND e.status='ACTIVE' AND s.status IN ('PENDING','ACTIVE')
               ORDER BY e."serviceDate",e."mealType",e.id''',
            pid,
            start,
            end,
        )
        snapshots = await conn.fetch(
            '''SELECT ps.id,ps."serviceDate",ps."mealType",ps."adultPortions",ps."childPortions",
                      ps."entitlementCount",ps."sourceFingerprint",ps."sourceMaxUpdatedAt",ps."cutoffAt",
                      ps."capturedAt",ps."capturedById",ps.reason,ps.forced,ps.notes,u."displayName" AS captured_by_name
               FROM dining_production_snapshots ps
               LEFT JOIN staff_users u ON u.id=ps."capturedById"
               WHERE ps."propertyId"=$1 AND ps."serviceDate" BETWEEN $2 AND $3''',
            pid,
            start,
            end,
        )
        settings = await load_settings(conn, pid)

    grouped: dict[tuple[date, str], list[Any]] = {}
    for row in source_rows:
        grouped.setdefault((row["serviceDate"], row["mealType"]), []).append(row)
    snapshot_by_key = {(row["serviceDate"], row["mealType"]): row for row in snapshots}

    days: list[dict[str, Any]] = []
    day = start
    while day <= end:
        meals: list[dict[str, Any]] = []
        for meal in MEALS:
            current = aggregate_rows(grouped.get((day, meal), []))
            setting_key = {
                "BREAKFAST": "breakfast_start",
                "LUNCH": "lunch_start",
                "DINNER": "dinner_start",
            }[meal]
            start_time = settings[setting_key]
            now = datetime.now(tz)
            if start_time is None:
                cutoff = {
                    "status": "UNCONFIGURED",
                    "meal_start": None,
                    "cutoff_at": None,
                    "cutoff_minutes": int(settings["meal_order_cutoff_minutes"]),
                }
            else:
                meal_at = datetime.combine(day, start_time, tzinfo=tz)
                cutoff_at = meal_at - timedelta(minutes=int(settings["meal_order_cutoff_minutes"]))
                cutoff = {
                    "status": "CUTOFF_REACHED" if now >= cutoff_at else "BEFORE_CUTOFF",
                    "meal_start": meal_at,
                    "cutoff_at": cutoff_at,
                    "cutoff_minutes": int(settings["meal_order_cutoff_minutes"]),
                }
            meals.append(
                {
                    "service_date": day,
                    "meal_type": meal,
                    "current_adult_portions": current["adult_portions"],
                    "current_child_portions": current["child_portions"],
                    "current_total_portions": current["total_portions"],
                    "current_entitlement_count": current["entitlement_count"],
                    **snapshot_payload(snapshot_by_key.get((day, meal)), current, cutoff),
                }
            )
        days.append({"service_date": day, "meals": meals})
        day += timedelta(days=1)

    return {
        "from_date": start,
        "through_date": end,
        "days": days,
        "truth": "Frozen production baselines are immutable snapshots of active dining entitlements; later changes are shown as deltas and do not rewrite the baseline.",
    }


@router.post("/production-snapshots", status_code=status.HTTP_201_CREATED)
async def create_production_snapshot(
    payload: ProductionSnapshotCreate,
    request: Request,
    user: dict[str, Any] = Depends(capture_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                f"dining-production-snapshot:{pid}:{payload.service_date}:{payload.meal_type}",
            )
            existing = await conn.fetchrow(
                '''SELECT ps.id,ps."serviceDate",ps."mealType",ps."adultPortions",ps."childPortions",
                          ps."entitlementCount",ps."sourceFingerprint",ps."sourceMaxUpdatedAt",ps."cutoffAt",
                          ps."capturedAt",ps."capturedById",ps.reason,ps.forced,ps.notes,u."displayName" AS captured_by_name
                   FROM dining_production_snapshots ps
                   LEFT JOIN staff_users u ON u.id=ps."capturedById"
                   WHERE ps."propertyId"=$1 AND ps."serviceDate"=$2 AND ps."mealType"=$3''',
                pid,
                payload.service_date,
                payload.meal_type,
            )
            current = aggregate_rows(await current_rows(conn, pid, payload.service_date, payload.meal_type))
            cutoff = await cutoff_info(conn, pid, payload.service_date, payload.meal_type)
            if existing:
                return {
                    "id": str(existing["id"]),
                    "idempotent": True,
                    "service_date": payload.service_date,
                    "meal_type": payload.meal_type,
                    **snapshot_payload(existing, current, cutoff),
                }

            if payload.force_before_cutoff and user["role"] not in {"OWNER", "MANAGER"}:
                raise HTTPException(status_code=403, detail={"code": "DINING_PRODUCTION_FORCE_MANAGER_ONLY"})
            if cutoff["status"] == "UNCONFIGURED" and not payload.force_before_cutoff:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_PRODUCTION_SNAPSHOT_TIME_NOT_CONFIGURED",
                        "meal_type": payload.meal_type,
                        "message": "Management must configure the meal start time before Chef OS can freeze the cutoff baseline.",
                    },
                )
            if cutoff["status"] == "BEFORE_CUTOFF" and not payload.force_before_cutoff:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "DINING_PRODUCTION_SNAPSHOT_TOO_EARLY",
                        "meal_type": payload.meal_type,
                        "cutoff_at": cutoff["cutoff_at"].isoformat(),
                    },
                )

            if cutoff["status"] == "UNCONFIGURED":
                reason = "MANAGER_FORCE_TIME_UNCONFIGURED"
            elif cutoff["status"] == "BEFORE_CUTOFF":
                reason = "MANAGER_FORCE_BEFORE_CUTOFF"
            else:
                reason = "CUTOFF"

            snapshot_id = uuid.uuid4()
            row = await conn.fetchrow(
                '''INSERT INTO dining_production_snapshots (
                     id,"propertyId","serviceDate","mealType","adultPortions","childPortions","entitlementCount",
                     "sourceFingerprint","sourceMaxUpdatedAt","cutoffAt","capturedAt","capturedById",reason,forced,notes,"createdAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,now(),$11,$12,$13,$14,now())
                   RETURNING id,"serviceDate","mealType","adultPortions","childPortions","entitlementCount",
                     "sourceFingerprint","sourceMaxUpdatedAt","cutoffAt","capturedAt","capturedById",reason,forced,notes''',
                snapshot_id,
                pid,
                payload.service_date,
                payload.meal_type,
                current["adult_portions"],
                current["child_portions"],
                current["entitlement_count"],
                current["source_fingerprint"],
                current["source_max_updated_at"],
                cutoff["cutoff_at"],
                uuid.UUID(user["id"]),
                reason,
                bool(payload.force_before_cutoff),
                payload.notes,
            )
            await audit(
                conn,
                pid,
                user,
                "CAPTURE_DINING_PRODUCTION_SNAPSHOT",
                str(snapshot_id),
                {
                    "service_date": payload.service_date,
                    "meal_type": payload.meal_type,
                    "adult_portions": current["adult_portions"],
                    "child_portions": current["child_portions"],
                    "entitlement_count": current["entitlement_count"],
                    "source_fingerprint": current["source_fingerprint"],
                    "cutoff_at": cutoff["cutoff_at"],
                    "reason": reason,
                    "forced": bool(payload.force_before_cutoff),
                },
            )
            snapshot = {**dict(row), "captured_by_name": user["display_name"]}

    return {
        "id": str(snapshot_id),
        "idempotent": False,
        "service_date": payload.service_date,
        "meal_type": payload.meal_type,
        **snapshot_payload(snapshot, current, cutoff),
        "truth": "Snapshot freezes production entitlement counts only; it does not create a charge or Payment.",
    }
