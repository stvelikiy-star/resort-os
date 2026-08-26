#!/usr/bin/env python3
import asyncio
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

import asyncpg


TRUE_VALUES = {"1", "true", "yes", "on"}
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")


def truthy(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def database_dsn() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value.split("?", 1)[0]


def parse_utc_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def static_checks() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if os.environ.get("APP_ENV", "").strip().lower() != "production":
        errors.append("APP_ENV must be production")
    if not truthy("COOKIE_SECURE"):
        errors.append("COOKIE_SECURE must be true")

    cookie_domain = os.environ.get("COOKIE_DOMAIN", "").strip()
    if truthy("REQUIRE_COOKIE_DOMAIN") and not cookie_domain:
        errors.append("COOKIE_DOMAIN is required because REQUIRE_COOKIE_DOMAIN=true")
    elif not cookie_domain:
        warnings.append("COOKIE_DOMAIN is empty; sessions will use host-only cookies. Verify this matches reverse-proxy/hostname design")

    if os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "").strip():
        errors.append("BOOTSTRAP_OWNER_PASSWORD must be cleared after bootstrap")

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        errors.append("DATABASE_URL is required")
    else:
        try:
            parsed = urlsplit(database_url)
            if parsed.scheme not in {"postgres", "postgresql"}:
                errors.append("DATABASE_URL must use PostgreSQL")
            if parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                warnings.append("DATABASE_URL points to localhost; verify this is intentional for the target environment")
        except ValueError:
            errors.append("DATABASE_URL is invalid")

    service_key = os.environ.get("AUTOMATION_SERVICE_KEY", "").strip()
    if truthy("REQUIRE_AUTOMATION_SERVICE", default=True) and not service_key:
        errors.append("AUTOMATION_SERVICE_KEY is required for the n8n/Core production boundary")
    elif service_key and len(service_key) < 32:
        errors.append("AUTOMATION_SERVICE_KEY must be at least 32 characters when configured")

    # Direct Telegram Sales is optional/reference under the n8n-first client architecture.
    # If someone configures it, require the matching webhook secret.
    if os.environ.get("TELEGRAM_SALES_BOT_TOKEN") and not os.environ.get("TELEGRAM_SALES_WEBHOOK_SECRET"):
        errors.append("Telegram Sales token is set but TELEGRAM_SALES_WEBHOOK_SECRET is missing")

    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("OPENAI_TRANSCRIBE_MODEL") and not os.environ.get("TELEGRAM_STAFF_WEBHOOK_SECRET"):
        errors.append("Staff voice transcription is configured but TELEGRAM_STAFF_WEBHOOK_SECRET is missing")

    if os.environ.get("OPENAI_API_KEY") and not (os.environ.get("OPENAI_SALES_MODEL") or os.environ.get("OPENAI_TRANSCRIBE_MODEL")):
        warnings.append("OPENAI_API_KEY is set but no Resort OS OpenAI model is configured")

    if os.environ.get("NFC_UID_PEPPER"):
        warnings.append("NFC_UID_PEPPER is set although NFC is deferred; active Resort Core should not compose NFC routes")

    return errors, warnings


async def database_checks() -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    facts: dict = {}
    conn = await asyncpg.connect(database_dsn(), timeout=10)
    try:
        property_row = await conn.fetchrow("SELECT id,name,timezone,currency FROM properties WHERE code=$1", PROPERTY_CODE)
        if not property_row:
            errors.append(f"Property {PROPERTY_CODE} is not loaded")
            return errors, warnings, facts
        property_id = property_row["id"]
        facts["property"] = {"code": PROPERTY_CODE, "name": property_row["name"], "timezone": property_row["timezone"], "currency": property_row["currency"]}

        facts["rooms"] = await conn.fetchval('SELECT COUNT(*) FROM rooms WHERE "propertyId"=$1', property_id)
        facts["room_types"] = await conn.fetchval('SELECT COUNT(*) FROM room_types WHERE "propertyId"=$1', property_id)
        facts["rate_periods"] = await conn.fetchval('''SELECT COUNT(*) FROM rate_periods rp JOIN rate_plans p ON p.id=rp."ratePlanId" WHERE p."propertyId"=$1''', property_id)
        facts["active_staff"] = await conn.fetchval('SELECT COUNT(*) FROM staff_users WHERE "propertyId"=$1 AND "isActive"=true', property_id)

        if facts["rooms"] <= 0:
            errors.append("No rooms loaded")
        if facts["room_types"] <= 0:
            errors.append("No room types loaded")
        if facts["rate_periods"] <= 0:
            errors.append("No rate periods loaded")
        if facts["active_staff"] <= 0:
            warnings.append("No active staff users found")

        expected_rooms = os.environ.get("EXPECTED_ROOM_COUNT", "").strip()
        if expected_rooms:
            try:
                expected = int(expected_rooms)
                if facts["rooms"] != expected:
                    errors.append(f"Room count mismatch: expected {expected}, found {facts['rooms']}")
            except ValueError:
                errors.append("EXPECTED_ROOM_COUNT must be an integer")

        expected_room_types = os.environ.get("EXPECTED_ROOM_TYPE_COUNT", "").strip()
        if expected_room_types:
            try:
                expected = int(expected_room_types)
                if facts["room_types"] != expected:
                    errors.append(f"Room type count mismatch: expected {expected}, found {facts['room_types']}")
            except ValueError:
                errors.append("EXPECTED_ROOM_TYPE_COUNT must be an integer")

        required_constraints = {
            "no_overlapping_active_room_blocks",
            "reservation_valid_dates",
            "reservation_request_valid_dates",
            "payment_positive_amount",
        }
        found_rows = await conn.fetch(
            '''SELECT conname FROM pg_constraint WHERE conname = ANY($1::text[])''',
            list(required_constraints),
        )
        found_names = {row["conname"] for row in found_rows}
        missing = sorted(required_constraints - found_names)
        if missing:
            errors.append("Missing critical PostgreSQL constraints: " + ", ".join(missing))
        facts["critical_constraints"] = sorted(found_names)

        migration_table = await conn.fetchval("SELECT to_regclass('public._prisma_migrations')")
        facts["migration_history_present"] = migration_table is not None
        if truthy("REQUIRE_MIGRATION_HISTORY", default=True):
            if migration_table is None:
                errors.append("_prisma_migrations is missing; production migration baseline has not been established")
            else:
                failed = await conn.fetchval('SELECT COUNT(*) FROM _prisma_migrations WHERE finished_at IS NULL OR rolled_back_at IS NOT NULL')
                applied = await conn.fetchval('SELECT COUNT(*) FROM _prisma_migrations WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL')
                facts["applied_migrations"] = applied
                if applied <= 0:
                    errors.append("No completed Prisma migrations recorded")
                if failed > 0:
                    errors.append(f"Migration history contains {failed} unfinished/rolled-back migration(s)")

        if truthy("REQUIRE_RECENT_BACKUP", default=True):
            backup_marker = os.environ.get("LAST_VERIFIED_BACKUP_AT", "").strip()
            if not backup_marker:
                errors.append("LAST_VERIFIED_BACKUP_AT is required after a successful backup/restore verification")
            else:
                try:
                    backup_at = parse_utc_timestamp(backup_marker)
                    facts["last_verified_backup_at"] = backup_at.isoformat()
                    if backup_at > datetime.now(timezone.utc):
                        errors.append("LAST_VERIFIED_BACKUP_AT cannot be in the future")
                    max_age_raw = os.environ.get("MAX_BACKUP_AGE_HOURS", "").strip()
                    if max_age_raw:
                        max_age = float(max_age_raw)
                        if max_age <= 0:
                            errors.append("MAX_BACKUP_AGE_HOURS must be positive")
                        else:
                            age_hours = (datetime.now(timezone.utc) - backup_at).total_seconds() / 3600
                            facts["verified_backup_age_hours"] = round(age_hours, 2)
                            if age_hours > max_age:
                                errors.append(f"Verified backup is too old: {age_hours:.1f}h > {max_age:.1f}h")
                except (ValueError, OverflowError):
                    errors.append("LAST_VERIFIED_BACKUP_AT must be a valid ISO-8601 timestamp")
    finally:
        await conn.close()
    return errors, warnings, facts


async def main() -> int:
    errors, warnings = static_checks()
    facts = {}
    if not any(item.startswith("DATABASE_URL") for item in errors):
        try:
            db_errors, db_warnings, facts = await database_checks()
            errors.extend(db_errors)
            warnings.extend(db_warnings)
        except Exception as exc:
            errors.append(f"Database preflight failed: {exc.__class__.__name__}: {exc}")

    print("Three Crowns production preflight")
    for warning in warnings:
        print(f"WARN: {warning}")
    for key, value in facts.items():
        print(f"FACT: {key}={value}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: NOT READY")
        return 1
    print("RESULT: READY FOR NEXT DEPLOYMENT GATE")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
