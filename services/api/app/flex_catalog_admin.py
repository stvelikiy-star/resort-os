"""Isolated MARINA FLEX SUPER_ADMIN catalog and subscription draft service.

Only adds PLANNED SKUs, immutable future price versions and OFF-only subscription
configuration proposals. It never modifies existing flex_subscriptions, payments,
invoices, hotel staff, entitlements or operational PMS.
Run with a dedicated NOINHERIT flex_catalog_draft_writer role on FLEX QA DB only.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP
import json
from calendar import monthrange
import os
import re
import uuid

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .flex_control_plane import (
    lifespan as core_lifespan,
    resolve_platform_principal,
    qa_password_reads,
)
from .flex_foundation import PlatformPrincipal

SKU_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9_.:-]{2,119}$")
DECIMAL_RE = re.compile(r"^(?:0|[1-9]\d{0,11})(?:\.\d{1,2})?$")
WRITER_ROLE = "flex_catalog_draft_writer"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("FLEX_ENVIRONMENT") != "qa" or os.environ.get(
        "FLEX_ENABLE_QA_CATALOG_DRAFTS"
    ) != "true":
        raise RuntimeError("FLEX catalog admin API may run only in explicitly approved QA")
    async with core_lifespan(app):
        async with app.state.flex_pool.acquire() as conn:
            elevated = await conn.fetchval(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
            member = await conn.fetchval(
                "SELECT pg_has_role(current_user,$1,'MEMBER')", WRITER_ROLE
            )
            inherited = await conn.fetchval(
                "SELECT pg_has_role(current_user,$1,'USAGE')", WRITER_ROLE
            )
            if elevated or not member or inherited:
                raise RuntimeError("FLEX catalog writer requires non-elevated NOINHERIT membership")
        yield


app = FastAPI(
    title="MARINA FLEX Catalog & Subscription Configuration QA",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None, redoc_url=None, openapi_url=None,
)


def require_admin(principal: PlatformPrincipal) -> None:
    allow_qa_password = qa_password_reads() and os.environ.get("FLEX_ENABLE_QA_CATALOG_DRAFTS") == "true"
    if principal.role != "SUPER_ADMIN" or not (principal.mfa_verified or allow_qa_password):
        raise HTTPException(403, detail="Verified FLEX SUPER_ADMIN with MFA required")


async def as_writer(conn, principal: PlatformPrincipal) -> None:
    require_admin(principal)
    await conn.execute(
        "SELECT set_config('flex.actor_subject_id',$1,true)", principal.subject_id
    )
    await conn.execute("SET LOCAL ROLE " + WRITER_ROLE)


class NewSku(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sku: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=160)
    capability_key: str = Field(min_length=3, max_length=120)

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, value: str) -> str:
        if not SKU_RE.fullmatch(value):
            raise ValueError("SKU must be uppercase stable identifier")
        return value

    @field_validator("capability_key")
    @classmethod
    def validate_capability(cls, value: str) -> str:
        if not CAPABILITY_RE.fullmatch(value):
            raise ValueError("Invalid capability key")
        return value


class FuturePrice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    monthly_price: str
    currency: str = "KGS"
    valid_from: datetime

    @field_validator("monthly_price")
    @classmethod
    def decimal_amount(cls, value: str) -> str:
        if not isinstance(value, str) or not DECIMAL_RE.fullmatch(value):
            raise ValueError("Use a non-negative KGS decimal string with up to 2 decimals")
        return value

    @field_validator("currency")
    @classmethod
    def only_kgs(cls, value: str) -> str:
        if value != "KGS":
            raise ValueError("Only KGS catalog prices are supported")
        return value

    @field_validator("valid_from")
    @classmethod
    def future_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Price activation needs timezone-aware timestamp")
        now = datetime.now(timezone.utc)
        if not (now + timedelta(days=1) < value <= now + timedelta(days=366)):
            raise ValueError("Price activation must be more than a day in the future")
        return value.astimezone(timezone.utc)


class NewConfigurationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    hotel_id: uuid.UUID
    title: str = Field(min_length=2, max_length=120)
    period_start: date
    period_end: date
    skus: list[str] = Field(min_length=1, max_length=50)

    @field_validator("skus")
    @classmethod
    def unique_skus(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not SKU_RE.fullmatch(s) for s in value):
            raise ValueError("Stable SKU identifiers must be unique")
        return value


class NewTariffPackageProposal(BaseModel):
    # Commercial offer only; NEVER a live tariff, subscription or module grant.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    hotel_id: uuid.UUID
    package_kind: str
    title: str = Field(min_length=2, max_length=120)
    period_start: date
    skus: list[str] = Field(max_length=50)
    commercial_policy_version: int | None = Field(default=None, strict=True, ge=1)
    term_months: int | None = Field(default=None, strict=True)
    include_implementation: bool = Field(default=False, strict=True)
    standard_term_discount: bool = Field(default=False, strict=True)
    launch_offer: bool = Field(default=False, strict=True)
    discount_pct: str = "0"
    trial_days: int = Field(default=0, ge=0, le=90)
    source_template_id: uuid.UUID | None = None
    custom_monthly_price: str | None = None

    @field_validator("package_kind")
    @classmethod
    def package_kind_allowed(cls, value: str) -> str:
        if value not in {"BASE", "BUSINESS", "PREMIUM", "CUSTOM"}:
            raise ValueError("Unknown tariff proposal kind")
        return value

    @field_validator("skus")
    @classmethod
    def package_skus(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value) or any(not SKU_RE.fullmatch(s) for s in value):
            raise ValueError("Non-unique or invalid SKU identifier")
        return value

    @field_validator("discount_pct")
    @classmethod
    def valid_discount(cls, value: str) -> str:
        if not isinstance(value, str) or not DECIMAL_RE.fullmatch(value):
            raise ValueError("Discount must be a decimal percentage string")
        if Decimal(value)>100:
            raise ValueError("Discount cannot exceed 100%")
        return value

    @field_validator("custom_monthly_price")
    @classmethod
    def valid_custom(cls, value: str | None) -> str | None:
        if value is not None and (not isinstance(value, str) or not DECIMAL_RE.fullmatch(value)):
            raise ValueError("Custom KGS price must be a non-negative decimal string")
        return value


def ensure_package_proposal(payload: NewTariffPackageProposal) -> None:
    if payload.launch_offer and (payload.commercial_policy_version is None or payload.package_kind == 'CUSTOM' or payload.term_months != 12 or payload.standard_term_discount or Decimal(payload.discount_pct) != 0 or payload.custom_monthly_price is not None or payload.source_template_id is not None):
        raise HTTPException(422, detail='Launch offer requires a standard annual package without combined discounts')
    if payload.term_months is not None and payload.term_months not in {1,3,6,12}:
        raise HTTPException(422, detail="Unsupported subscription term")
    if payload.commercial_policy_version is None and (payload.term_months is not None or payload.include_implementation or payload.standard_term_discount):
        raise HTTPException(422, detail="Commercial policy required")
    if payload.standard_term_discount and (Decimal(payload.discount_pct)!=0 or payload.custom_monthly_price is not None):
        raise HTTPException(422, detail="Choose standard term discount or individual terms")
    if payload.commercial_policy_version is None and not payload.skus:
        raise HTTPException(422, detail="Select at least one legacy SKU")
    if payload.commercial_policy_version is not None and payload.source_template_id is not None:
        raise HTTPException(422, detail="Legacy template cannot override commercial package")
    today = datetime.now(ZoneInfo("Asia/Bishkek")).date()
    if not (today-timedelta(days=1) <= payload.period_start <= today+timedelta(days=366)):
        raise HTTPException(422, detail="Package start date out of range")
    if payload.custom_monthly_price is not None and (
        payload.package_kind!="CUSTOM" or Decimal(payload.discount_pct)!=0
    ):
        raise HTTPException(422, detail="Only CUSTOM without discount can override price")


def ensure_draft_period(payload: NewConfigurationDraft) -> None:
    today = datetime.now(ZoneInfo('Asia/Bishkek')).date()
    if (
        payload.period_end < payload.period_start
        or (payload.period_end - payload.period_start).days > 366
        or payload.period_start < today - timedelta(days=1)
        or payload.period_start > today + timedelta(days=366)
    ):
        raise HTTPException(422, detail="Draft dates must be current or future, at most 366 days")


def _price_row(row) -> dict:
    return {
        "version": row["version"],
        "monthly_price": str(row["monthly_price"]),
        "currency": row["currency"].strip(),
        "valid_from": row["valid_from"].isoformat(),
        "valid_to": row["valid_to"].isoformat() if row["valid_to"] else None,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok", "mode": "QA_CATALOG_CONFIGURATION",
        "payments_enabled": False, "subscriptions_activated": False,
    }


@app.get("/v1/platform/launch-offer")
async def launch_offer_status(
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            rows = await conn.fetch(
                "SELECT r.hotel_id,r.slot,r.offer_id,r.created_at,h.display_name,"
                "p.package_kind,p.subscription_term_total,p.implementation_total "
                "FROM flex_launch_offer_reservations r JOIN flex_hotels h ON h.id=r.hotel_id "
                "JOIN flex_tariff_package_versions p ON p.id=r.offer_id ORDER BY r.slot"
            )
            return {"capacity":50,"reserved":len(rows),"available":50-len(rows),
                    "reservations":[dict(r) for r in rows],"payments_enabled":False}


@app.get("/v1/platform/commercial-policy")
async def commercial_policy(
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            row = await conn.fetchrow(
                "SELECT version,policy,created_at FROM flex_commercial_policy_versions "
                "ORDER BY version DESC LIMIT 1"
            )
            if row is None:
                raise HTTPException(404, detail="Commercial policy unavailable")
            policy = json.loads(row["policy"]) if isinstance(row["policy"], str) else row["policy"]
            return {"version": row["version"], "policy": policy,
                    "created_at": row["created_at"].isoformat()}



class CommercialPriceChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(strict=True, ge=1, le=2147483646)
    price_kind: str
    code: str
    monthly_price: str

    @field_validator("monthly_price")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        if not DECIMAL_RE.fullmatch(value) or Decimal(value) <= 0:
            raise ValueError("Positive KGS amount required")
        return value


@app.post("/v1/platform/commercial-policy", status_code=201)
async def change_commercial_price(
    payload: CommercialPriceChange, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn, principal)
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext('flex_commercial_policy_revision'))")
            row = await conn.fetchrow(
                "SELECT version,policy FROM flex_commercial_policy_versions ORDER BY version DESC LIMIT 1"
            )
            if row is None or row["version"] != payload.expected_version:
                raise HTTPException(409, detail="Commercial policy version changed; reload")
            policy = json.loads(row["policy"]) if isinstance(row["policy"], str) else row["policy"]
            amount = format(Decimal(payload.monthly_price), ".2f")
            if payload.price_kind == "PACKAGE" and payload.code in {"BASE","BUSINESS","PREMIUM"}:
                policy["monthly_packages"][payload.code]["price"] = amount
                if payload.code == "BASE":
                    policy["monthly_packages"]["CUSTOM"]["minimum"] = amount
                    policy["monthly_packages"]["CUSTOM"]["base_price"] = amount
            elif payload.price_kind == "MODULE" and payload.code in policy["module_monthly_prices"]:
                policy["module_monthly_prices"][payload.code] = amount
            else:
                raise HTTPException(422, detail="Unknown commercial price code")
            version = row["version"] + 1
            await conn.execute(
                "INSERT INTO flex_commercial_policy_versions(version,policy,created_by) VALUES($1,$2::jsonb,$3)",
                version, json.dumps(policy), principal.subject_id
            )
            return {"version": version, "policy": policy, "entitlement_changed": False,
                    "payment_collected": False}


class InstallationConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hotel_id: uuid.UUID


@app.get("/v1/platform/installation-trial")
async def installation_trial(request: Request, hotel_id: uuid.UUID = Query(...),
    principal: PlatformPrincipal = Depends(resolve_platform_principal)):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            row = await conn.fetchrow(
                "SELECT hotel_id,completed_at,trial_start,trial_end_exclusive FROM flex_installation_completions WHERE hotel_id=$1",hotel_id)
            return dict(row) if row else None


@app.post("/v1/platform/installation-trial", status_code=201)
async def confirm_installation(payload: InstallationConfirmation, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal)):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn, principal)
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))","FLEX_INSTALL_"+str(payload.hotel_id))
            hotel=await conn.fetchval("SELECT status FROM flex_hotels WHERE id=$1",payload.hotel_id)
            if hotel not in {"PENDING","ACTIVE"}:
                raise HTTPException(404,detail="Commercial hotel unavailable")
            await conn.execute(
                "INSERT INTO flex_installation_completions(hotel_id,completed_by,trial_start,trial_end_exclusive) "
                "VALUES($1,$2,(now() AT TIME ZONE 'Asia/Bishkek')::date,(now() AT TIME ZONE 'Asia/Bishkek')::date+5) "
                "ON CONFLICT(hotel_id) DO NOTHING",payload.hotel_id,principal.subject_id)
            row=await conn.fetchrow(
                "SELECT hotel_id,completed_at,trial_start,trial_end_exclusive FROM flex_installation_completions WHERE hotel_id=$1",payload.hotel_id)
            return {**dict(row),"entitlement_changed":False,"payment_collected":False}

@app.get("/v1/platform/catalog")
async def catalog(
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            rows = await conn.fetch(
                "SELECT s.sku,s.title,s.capability_key,s.product_status,s.is_core,"
                " p.version,p.monthly_price,p.currency,p.valid_from,p.valid_to "
                "FROM flex_skus s LEFT JOIN LATERAL ( "
                "SELECT version,monthly_price,currency,valid_from,valid_to "
                "FROM flex_price_versions "
                "WHERE sku=s.sku ORDER BY version DESC LIMIT 1 "
                ") p ON true ORDER BY s.created_at DESC,s.sku LIMIT 200"
            )
            return [
                {
                    "sku": r["sku"], "name": r["title"],
                    "capability": r["capability_key"], "status": r["product_status"],
                    "is_core": r["is_core"],
                    "latest_price": _price_row(r) if r["version"] is not None else None,
                }
                for r in rows
            ]


@app.get("/v1/platform/catalog/skus/{sku}/versions")
async def price_versions(
    sku: str, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    if not SKU_RE.fullmatch(sku):
        raise HTTPException(404, detail="Unknown SKU")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            found = await conn.fetchval("SELECT true FROM flex_skus WHERE sku=$1", sku)
            if not found:
                raise HTTPException(404, detail="Unknown SKU")
            rows = await conn.fetch(
                "SELECT version,monthly_price,currency,valid_from,valid_to "
                "FROM flex_price_versions WHERE sku=$1 ORDER BY version DESC LIMIT 100",
                sku,
            )
            return {"sku": sku, "versions": [_price_row(r) for r in rows]}


@app.post("/v1/platform/catalog/skus", status_code=201)
async def create_planned_sku(
    payload: NewSku, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        try:
            async with conn.transaction():
                await as_writer(conn, principal)
                await conn.execute(
                    "INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core) "
                    "VALUES($1,$2,$3,'PLANNED',false)",
                    payload.sku, payload.title, payload.capability_key,
                )
                return {
                    "sku": payload.sku, "status": "PLANNED",
                    "capability": payload.capability_key,
                    "published": False, "entitlement_changed": False,
                }
        except asyncpg.UniqueViolationError:
            raise HTTPException(409, detail="SKU already exists") from None


@app.post("/v1/platform/catalog/skus/{sku}/prices", status_code=201)
async def add_future_price(
    sku: str, payload: FuturePrice, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    if not SKU_RE.fullmatch(sku):
        raise HTTPException(404, detail="Invalid SKU")
    async with request.app.state.flex_pool.acquire() as conn:
        try:
            async with conn.transaction():
                await as_writer(conn, principal)
                await conn.fetchval(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                    "FLEX_PRICE_" + sku,
                )
                sku_row = await conn.fetchrow(
                    "SELECT product_status,is_core FROM flex_skus WHERE sku=$1", sku
                )
                if sku_row is None:
                    raise HTTPException(404, detail="SKU not found")
                if sku_row["is_core"] or sku_row["product_status"] not in {"PLANNED","AVAILABLE"}:
                    raise HTTPException(409, detail="Core or unavailable SKU cannot receive new price")
                row = await conn.fetchrow(
                    "SELECT version,valid_from FROM flex_price_versions "
                    "WHERE sku=$1 ORDER BY version DESC LIMIT 1",
                    sku,
                )
                if row and payload.valid_from <= row["valid_from"]:
                    raise HTTPException(409, detail="New price must start after prior version")
                next_version = (row["version"] if row else 0) + 1
                await conn.execute(
                    "INSERT INTO flex_price_versions(sku,version,currency,monthly_price,valid_from) "
                    "VALUES($1,$2,'KGS',$3,$4)",
                    sku, next_version, Decimal(payload.monthly_price), payload.valid_from,
                )
                return {
                    "sku": sku, "version": next_version,
                    "monthly_price": payload.monthly_price, "currency": "KGS",
                    "valid_from": payload.valid_from.isoformat(),
                    "payment_collected": False, "entitlement_changed": False,
                }
        except (asyncpg.UniqueViolationError, asyncpg.CheckViolationError):
            raise HTTPException(409, detail="Price version conflict") from None


class PublishTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    package_id: uuid.UUID


# Extract only module identifiers from the immutable source. The catalog never
# projects the source hotel's title, discount, trial or negotiated price.
TEMPLATE_SELECT = """
    SELECT t.id, t.package_kind, t.revision,
           ARRAY(SELECT item->>'sku' FROM jsonb_array_elements(p.sku_snapshot) item
                 ORDER BY item->>'sku') AS skus
    FROM flex_tariff_templates t JOIN flex_tariff_package_versions p ON p.id=t.id
"""


@app.get("/v1/platform/tariff-templates")
async def list_tariff_templates(
    request: Request, principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            rows = await conn.fetch(
                "SELECT DISTINCT ON (package_kind) * FROM (" + TEMPLATE_SELECT +
                ") versions ORDER BY package_kind, revision DESC"
            )
            return [dict(row) for row in rows]


@app.post("/v1/platform/tariff-templates", status_code=201)
async def publish_tariff_template(
    payload: PublishTemplate, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn, principal)
            kind = await conn.fetchval(
                "SELECT package_kind FROM flex_tariff_package_versions WHERE id=$1", payload.package_id
            )
            if kind is None:
                raise HTTPException(404, detail="Package version unavailable")
            if kind == "CUSTOM":
                raise HTTPException(422, detail="Choose a standard package")
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                               "FLEX_TEMPLATE_" + kind)
            await conn.execute(
                "INSERT INTO flex_tariff_templates (id, package_kind, revision, created_by) "
                "SELECT $1, $2, coalesce(max(revision), 0) + 1, $3 "
                "FROM flex_tariff_templates WHERE package_kind=$2 ON CONFLICT (id) DO NOTHING",
                payload.package_id, kind, principal.subject_id,
            )
            return dict(await conn.fetchrow(TEMPLATE_SELECT + " WHERE t.id=$1", payload.package_id))


@app.get("/v1/platform/tariff-packages")
async def tariff_packages(
    request: Request,
    hotel_id: uuid.UUID = Query(...),
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            rows = await conn.fetch(
                "SELECT id,hotel_id,package_kind,version,title,sku_snapshot,source_template_id,"
                "list_monthly_total,discount_pct,trial_days,custom_monthly_price,"
                "proposed_monthly_total,state,enforcement,currency,created_at,commercial_policy_version,term_months,period_start,period_end_exclusive,subscription_term_total,implementation_total "
                "FROM flex_tariff_package_versions WHERE hotel_id=$1 "
                "ORDER BY created_at DESC,id DESC LIMIT 100",
                hotel_id,
            )
            return [
                {
                    "id":str(r["id"]), "hotel_id":str(r["hotel_id"]),
                    "package_kind":r["package_kind"], "version":r["version"],
                    "source_template_id":r["source_template_id"],
                    "title":r["title"],
                    "commercial_policy_version":r["commercial_policy_version"],"term_months":r["term_months"],
                    "period_start":r["period_start"],"period_end_exclusive":r["period_end_exclusive"],
                    "subscription_term_total":str(r["subscription_term_total"]) if r["subscription_term_total"] is not None else None,
                    "implementation_total":str(r["implementation_total"]) if r["implementation_total"] is not None else None,
                    "items":json.loads(r["sku_snapshot"]) if isinstance(r["sku_snapshot"],str) else r["sku_snapshot"],
                    "list_monthly_total":str(r["list_monthly_total"]),
                    "discount_pct":str(r["discount_pct"]),
                    "trial_days":r["trial_days"],
                    "custom_monthly_price":str(r["custom_monthly_price"]) if r["custom_monthly_price"] is not None else None,
                    "proposed_monthly_total":str(r["proposed_monthly_total"]),
                    "state":r["state"], "enforcement":r["enforcement"],
                    "currency":r["currency"].strip(),
                    "created_at":r["created_at"].isoformat(),
                } for r in rows
            ]


@app.post("/v1/platform/tariff-packages", status_code=201)
async def create_tariff_package_proposal(
    payload: NewTariffPackageProposal,
    request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    ensure_package_proposal(payload)
    async with request.app.state.flex_pool.acquire() as conn:
        try:
            async with conn.transaction():
                await as_writer(conn, principal)
                await conn.fetchval(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                    "FLEX_PACKAGE_"+str(payload.hotel_id)+"_"+payload.package_kind,
                )
                if payload.source_template_id is not None:
                    template = await conn.fetchrow(TEMPLATE_SELECT + " WHERE t.id=$1", payload.source_template_id)
                    if (not template or template["package_kind"] != payload.package_kind or
                            set(template["skus"]) != set(payload.skus)):
                        raise HTTPException(422, detail="Template and selected modules do not match")
                hotel = await conn.fetchval(
                    "SELECT status FROM flex_hotels WHERE id=$1",payload.hotel_id
                )
                if hotel not in {"PENDING","ACTIVE"}:
                    raise HTTPException(404, detail="Commercial hotel unavailable")
                if payload.commercial_policy_version is not None:
                    policy_row = await conn.fetchrow(
                        "SELECT version,policy FROM flex_commercial_policy_versions ORDER BY version DESC LIMIT 1"
                    )
                    if not policy_row or policy_row["version"] != payload.commercial_policy_version:
                        raise HTTPException(409, detail="Commercial policy version changed; reload")
                    policy = json.loads(policy_row["policy"]) if isinstance(policy_row["policy"],str) else policy_row["policy"]
                    package = policy["monthly_packages"][payload.package_kind]
                    prices = policy["module_monthly_prices"]
                    included = set(package["modules"])
                    selected = set(payload.skus)
                    if not selected.issubset(prices):
                        raise HTTPException(422, detail="Unknown commercial module")
                    base = Decimal(str(package.get("price",package.get("base_price"))))
                    extra = selected - included
                    if payload.launch_offer:
                        if extra or policy['launch_offer'] != {'discount_pct':40,'months':12,'first_hotels':50,'first_year_only':True,'prepayment_required':True}:
                            raise HTTPException(422, detail='Launch offer policy or add-ons not eligible')
                        await conn.fetchval("SELECT pg_advisory_xact_lock(hashtext('FLEX_LAUNCH_OFFER_50'))")
                        if await conn.fetchval('SELECT EXISTS(SELECT 1 FROM flex_launch_offer_reservations WHERE hotel_id=$1)', payload.hotel_id):
                            raise HTTPException(409, detail='Hotel already has a launch reservation')
                        launch_slot = await conn.fetchval('SELECT min(n) FROM generate_series(1,50) n WHERE NOT EXISTS(SELECT 1 FROM flex_launch_offer_reservations r WHERE r.slot=n)')
                        if launch_slot is None:
                            raise HTTPException(409, detail='Launch offer capacity exhausted')
                    list_total = base + sum((Decimal(str(prices[k])) for k in extra),Decimal("0"))
                    if payload.custom_monthly_price is not None and Decimal(payload.custom_monthly_price) < base:
                        raise HTTPException(422, detail="CUSTOM price below mandatory base")
                    items = [{"sku":"BASE_PMS","monthly_price":str(base),"currency":"KGS",
                              "commercial_policy_version":policy_row["version"],"pricing_source":"COMMERCIAL_PACKAGE"}]
                    items.extend({"sku":k,"monthly_price":str(Decimal("0") if k in included else Decimal(str(prices[k]))),
                                  "currency":"KGS","commercial_policy_version":policy_row["version"],
                                  "included_in_package":k in included} for k in sorted(included | selected))
                else:
                    rows = await conn.fetch(
                        "SELECT s.sku,p.id AS price_id,p.version,p.monthly_price,p.currency "
                        "FROM flex_skus s JOIN LATERAL ( "
                        "SELECT id,version,monthly_price,currency FROM flex_price_versions "
                        "WHERE sku=s.sku AND valid_from<=($2::date::timestamp AT TIME ZONE 'Asia/Bishkek') "
                        "AND (valid_to IS NULL OR valid_to>($2::date::timestamp AT TIME ZONE 'Asia/Bishkek')) "
                        "ORDER BY valid_from DESC,version DESC LIMIT 1 "
                        ") p ON true WHERE s.sku=ANY($1::text[]) "
                        "AND s.product_status='AVAILABLE' AND s.is_core=false AND p.currency='KGS' "
                        "ORDER BY s.sku",
                        payload.skus,payload.period_start,
                    )
                    if len(rows)!=len(payload.skus):
                        raise HTTPException(
                            422, detail="Only published non-core SKU prices effective on start date"
                        )
                    items=[
                        {"sku":r["sku"],"price_version_id":str(r["price_id"]),
                         "price_version":r["version"],"monthly_price":str(r["monthly_price"]),
                         "currency":"KGS"} for r in rows
                    ]
                    list_total=sum((r["monthly_price"] for r in rows),Decimal("0.00"))
                discount=Decimal(payload.discount_pct)
                months = start = end = term_total = implementation = None
                if payload.commercial_policy_version is not None:
                    months = payload.term_months or 1
                    start = payload.period_start
                    year, month = divmod(start.year*12+start.month-1+months,12)
                    end = date(year,month+1,min(start.day,monthrange(year,month+1)[1]))
                    if payload.standard_term_discount:
                        discount = Decimal(str(policy["term_discounts_pct"][str(months)]))
                    if payload.launch_offer:
                        discount = Decimal('40')
                    implementation = Decimal(str(policy["implementation_fee"])) if payload.include_implementation else Decimal("0")
                custom=(Decimal(payload.custom_monthly_price)
                        if payload.custom_monthly_price is not None else None)
                total=(custom if custom is not None else
                       list_total*(Decimal(100)-discount)/Decimal(100)).quantize(
                           Decimal("0.01"),rounding=ROUND_HALF_UP
                       )
                if months is not None:
                    term_total = ((custom if custom is not None else list_total*(Decimal(100)-discount)/Decimal(100))*months).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
                previous=await conn.fetchval(
                    "SELECT coalesce(max(version),0) FROM flex_tariff_package_versions "
                    "WHERE hotel_id=$1 AND package_kind=$2",
                    payload.hotel_id,payload.package_kind,
                )
                version=previous+1
                row=await conn.fetchrow(
                    "INSERT INTO flex_tariff_package_versions("
                    "hotel_id,package_kind,version,title,sku_snapshot,"
                    "list_monthly_total,discount_pct,trial_days,custom_monthly_price,"
                     "proposed_monthly_total,created_by,source_template_id,commercial_policy_version,term_months,period_start,period_end_exclusive,subscription_term_total,implementation_total) "
                    "VALUES($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18) "
                    "RETURNING id,created_at",
                    payload.hotel_id,payload.package_kind,version,payload.title,
                    json.dumps(items),list_total,discount,payload.trial_days,
                    custom,total,principal.subject_id,payload.source_template_id,payload.commercial_policy_version,months,start,end,term_total,implementation,
                )
                if payload.launch_offer:
                    await conn.execute('INSERT INTO flex_launch_offer_reservations(hotel_id,slot,offer_id,created_by) VALUES($1,$2,$3,$4)',payload.hotel_id,launch_slot,row['id'],principal.subject_id)
                return {
                    "launch_offer_reserved":payload.launch_offer,
                    "launch_offer_slot":launch_slot if payload.launch_offer else None,
                    "id":str(row["id"]),"hotel_id":str(payload.hotel_id),
                    "package_kind":payload.package_kind,"version":version,
                    "source_template_id":payload.source_template_id,
                    "items":items,"list_monthly_total":str(list_total),
                    "term_months":months,"period_start":start,"period_end_exclusive":end,
                    "subscription_term_total":str(term_total) if term_total is not None else None,
                    "implementation_total":str(implementation) if implementation is not None else None,
                    "discount_pct":str(discount),"trial_days":payload.trial_days,
                    "custom_monthly_price":str(custom) if custom is not None else None,
                    "proposed_monthly_total":str(total),"currency":"KGS",
                    "state":"DRAFT","enforcement":"OFF",
                    "subscription_activated":False,"payments_enabled":False,
                }
        except (asyncpg.UniqueViolationError,asyncpg.CheckViolationError):
            raise HTTPException(409,detail="Tariff proposal version conflict") from None


@app.get("/v1/platform/subscription-drafts")
async def drafts(
    request: Request,
    hotel_id: uuid.UUID | None = Query(None),
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn, principal)
            rows = await conn.fetch(
                "SELECT id,hotel_id,version,title,period_start,period_end,enforcement,state,"
                " currency,items,proposed_monthly_total,created_by,created_at "
                "FROM flex_subscription_configuration_drafts "
                "WHERE ($1::uuid IS NULL OR hotel_id=$1) "
                "ORDER BY created_at DESC,id DESC LIMIT 100",
                hotel_id,
            )
            return [
                {
                    "id": str(r["id"]), "hotel_id": str(r["hotel_id"]),
                    "version": r["version"], "title": r["title"],
                    "period_start": r["period_start"].isoformat(),
                    "period_end": r["period_end"].isoformat(),
                    "state": "DRAFT", "enforcement": "OFF",
                    "currency": "KGS", "items": json.loads(r['items']) if isinstance(r['items'], str) else r['items'],
                    "proposed_monthly_total": str(r["proposed_monthly_total"]),
                    "created_at": r["created_at"].isoformat(),
                }
                for r in rows
            ]


@app.post("/v1/platform/subscription-drafts", status_code=201)
async def create_configuration_draft(
    payload: NewConfigurationDraft, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    require_admin(principal)
    ensure_draft_period(payload)
    async with request.app.state.flex_pool.acquire() as conn:
        try:
            async with conn.transaction():
                await as_writer(conn, principal)
                await conn.fetchval(
                    "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                    "FLEX_DRAFT_" + str(payload.hotel_id),
                )
                hotel = await conn.fetchval(
                    "SELECT status FROM flex_hotels WHERE id=$1", payload.hotel_id
                )
                if hotel not in {"PENDING", "ACTIVE"}:
                    raise HTTPException(404, detail="Hotel is not available for a draft")
                rows = await conn.fetch(
                    "SELECT s.sku, p.id AS price_id,p.version,p.monthly_price,p.currency "
                    "FROM flex_skus s JOIN LATERAL ( "
                    "SELECT id,version,monthly_price,currency FROM flex_price_versions "
                    "WHERE sku=s.sku AND valid_from <= ($2::date::timestamp AT TIME ZONE 'Asia/Bishkek') "
                    "AND (valid_to IS NULL OR valid_to > ($2::date::timestamp AT TIME ZONE 'Asia/Bishkek')) "
                    "ORDER BY valid_from DESC,version DESC LIMIT 1 "
                    ") p ON true WHERE s.sku = ANY($1::text[]) AND s.product_status='AVAILABLE' "
                    "AND s.is_core=false ORDER BY s.sku",
                    payload.skus, payload.period_start,
                )
                if len(rows) != len(payload.skus):
                    raise HTTPException(
                        422, detail="Only published non-core SKU prices effective on period start"
                    )
                snapshots = [
                    {
                        "sku": r["sku"], "price_version_id": str(r["price_id"]),
                        "price_version": r["version"],
                        "monthly_price": str(r["monthly_price"]),
                        "currency": "KGS",
                    }
                    for r in rows
                ]
                total = sum((r["monthly_price"] for r in rows), Decimal("0.00"))
                previous = await conn.fetchval(
                    "SELECT coalesce(max(version),0) FROM flex_subscription_configuration_drafts "
                    "WHERE hotel_id=$1", payload.hotel_id,
                )
                version = previous + 1
                record = await conn.fetchrow(
                    "INSERT INTO flex_subscription_configuration_drafts("
                    "hotel_id,version,title,period_start,period_end,enforcement,state,"
                    "currency,items,proposed_monthly_total,created_by) "
                    "VALUES($1,$2,$3,$4,$5,'OFF','DRAFT','KGS',$6::jsonb,$7,$8) "
                    "RETURNING id,created_at",
                    payload.hotel_id, version, payload.title,
                    payload.period_start, payload.period_end,
                    json.dumps(snapshots, ensure_ascii=False),
                    total, principal.subject_id,
                )
                return {
                    "id": str(record["id"]), "hotel_id": str(payload.hotel_id),
                    "version": version, "state": "DRAFT", "enforcement": "OFF",
                    "items": snapshots, "currency": "KGS",
                    "proposed_monthly_total": str(total),
                    "subscription_activated": False, "payments_enabled": False,
                }
        except (asyncpg.UniqueViolationError, asyncpg.CheckViolationError):
            raise HTTPException(409, detail="Concurrent draft or invalid constraints") from None


class CustomerProfileRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    hotel_id: uuid.UUID
    expected_version: int = Field(strict=True, ge=0)
    contact_name: str = Field(max_length=180)
    contact_email: str = Field(max_length=254)
    contact_phone: str = Field(max_length=40)
    responsible_name: str = Field(max_length=180)

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, value):
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid contact email")
        return value


class AgreementDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hotel_id: uuid.UUID
    offer_id: uuid.UUID


class InvoicePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hotel_id: uuid.UUID
    agreement_id: uuid.UUID


async def commercial_hotel_lock(conn, hotel_id):
    await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", "FLEX_CUSTOMER:"+str(hotel_id))
    if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM flex_hotels WHERE id=$1 AND status IN ('PENDING','ACTIVE'))",hotel_id):
        raise HTTPException(404,detail="Commercial hotel unavailable")


@app.get("/v1/platform/customer-profile")
async def customer_profile(request: Request, hotel_id: uuid.UUID=Query(...),
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn,principal)
            rows=await conn.fetch("SELECT * FROM flex_hotel_profile_versions WHERE hotel_id=$1 ORDER BY version DESC",hotel_id)
            return {"current":dict(rows[0]) if rows else None,"history":[dict(r) for r in rows]}


@app.post("/v1/platform/customer-profile",status_code=201)
async def save_customer_profile(payload: CustomerProfileRevision,request: Request,
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn,principal)
            await commercial_hotel_lock(conn,payload.hotel_id)
            version=await conn.fetchval("SELECT coalesce(max(version),0) FROM flex_hotel_profile_versions WHERE hotel_id=$1",payload.hotel_id)
            if version!=payload.expected_version:
                raise HTTPException(409,detail="Customer profile revision changed")
            row=await conn.fetchrow("INSERT INTO flex_hotel_profile_versions(hotel_id,version,contact_name,contact_email,contact_phone,responsible_name,created_by) VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING *",
                payload.hotel_id,version+1,payload.contact_name,payload.contact_email,payload.contact_phone,payload.responsible_name,principal.subject_id)
            return dict(row)


def draft_agreement_response(row):
    data=dict(row)
    if isinstance(data["terms"],str):
        data["terms"]=json.loads(data["terms"])
    return data


@app.get("/v1/platform/agreement-drafts")
async def agreement_drafts(request: Request,hotel_id: uuid.UUID=Query(...),
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await as_writer(conn,principal)
            rows=await conn.fetch("SELECT * FROM flex_commercial_agreement_versions WHERE hotel_id=$1 ORDER BY version DESC",hotel_id)
            previews=await conn.fetch("SELECT * FROM flex_non_issuable_invoice_previews WHERE hotel_id=$1 ORDER BY created_at DESC",hotel_id)
            return {"agreements":[draft_agreement_response(r) for r in rows],"previews":[dict(r) for r in previews]}


@app.post("/v1/platform/agreement-drafts",status_code=201)
async def create_agreement_draft(payload: AgreementDraftRequest,request: Request,
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    import hashlib
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn,principal)
            await commercial_hotel_lock(conn,payload.hotel_id)
            offer=await conn.fetchrow("SELECT * FROM flex_tariff_package_versions WHERE id=$1 AND hotel_id=$2 AND commercial_policy_version IS NOT NULL AND term_months IS NOT NULL",payload.offer_id,payload.hotel_id)
            if offer is None:
                raise HTTPException(404,detail="Versioned commercial offer unavailable for hotel")
            existing=await conn.fetchrow("SELECT * FROM flex_commercial_agreement_versions WHERE source_offer_id=$1",payload.offer_id)
            if existing:
                return draft_agreement_response(existing)
            version=await conn.fetchval("SELECT coalesce(max(version),0)+1 FROM flex_commercial_agreement_versions WHERE hotel_id=$1",payload.hotel_id)
            items=offer["sku_snapshot"]
            if isinstance(items,str):
                items=json.loads(items)
            terms={"source_offer_id":str(offer["id"]),"hotel_id":str(payload.hotel_id),
                "package_kind":offer["package_kind"],"policy_version":offer["commercial_policy_version"],
                "items":items,"currency":"KGS","term_months":offer["term_months"],
                "period_start":offer["period_start"].isoformat(),
                "period_end_exclusive":offer["period_end_exclusive"].isoformat(),
                "subscription_term_total":str(offer["subscription_term_total"]),
                "implementation_total":str(offer["implementation_total"]),
                "discount_pct":str(offer["discount_pct"]),"tax_status":"NOT_CALCULATED"}
            encoded=json.dumps(terms,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            digest=hashlib.sha256(encoded.encode()).hexdigest()
            row=await conn.fetchrow("INSERT INTO flex_commercial_agreement_versions(hotel_id,version,state,terms,terms_digest,effective_from,source_offer_id,draft_created_by) VALUES($1,$2,'DRAFT',$3::jsonb,$4,$5,$6,$7) RETURNING *",
                payload.hotel_id,version,encoded,digest,offer["period_start"],payload.offer_id,principal.subject_id)
            return draft_agreement_response(row)


@app.post("/v1/platform/invoice-previews",status_code=201)
async def create_invoice_preview(payload: InvoicePreviewRequest,request: Request,
    principal: PlatformPrincipal=Depends(resolve_platform_principal)):
    import hashlib
    require_admin(principal)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction():
            await as_writer(conn,principal)
            await commercial_hotel_lock(conn,payload.hotel_id)
            row=await conn.fetchrow("SELECT a.terms_digest,p.period_start,p.period_end_exclusive,p.subscription_term_total,p.implementation_total FROM flex_commercial_agreement_versions a JOIN flex_tariff_package_versions p ON p.id=a.source_offer_id WHERE a.id=$1 AND a.hotel_id=$2 AND a.state='DRAFT'",payload.agreement_id,payload.hotel_id)
            if row is None:
                raise HTTPException(404,detail="Draft agreement unavailable for hotel")
            amount=row["subscription_term_total"]+row["implementation_total"]
            if amount>=Decimal("10000000000000000"):
                raise HTTPException(422,detail="Preview amount exceeds storage limit")
            digest=hashlib.sha256(("FLEX_NON_ISSUABLE:"+str(payload.agreement_id)+":"+row["terms_digest"]).encode()).hexdigest()
            existing=await conn.fetchrow("SELECT * FROM flex_non_issuable_invoice_previews WHERE hotel_id=$1 AND agreement_version_id=$2 AND preview_sha256=$3",payload.hotel_id,payload.agreement_id,digest)
            if existing:
                return dict(existing)
            saved=await conn.fetchrow("INSERT INTO flex_non_issuable_invoice_previews(hotel_id,agreement_version_id,preview_sha256,quote_sha256,period_start,period_end,amount_before_unresolved_taxes) VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING *",
                payload.hotel_id,payload.agreement_id,digest,row["terms_digest"],row["period_start"],row["period_end_exclusive"]-timedelta(days=1),amount)
            return dict(saved)
