#!/usr/bin/env python3
"""Non-destructive Beget environment/network preflight.

This does not mutate PostgreSQL, S3, DNS, firewall or Docker. It validates the
managed infrastructure contract before deployment and can optionally prove basic
network reachability to the configured DBaaS and S3 endpoints.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

TRUE_VALUES = {"1", "true", "yes", "on"}
PLACEHOLDER_MARKERS = ("change_me", "example.invalid", "example.com")
TLS_SSLMODES = {"require", "verify-ca", "verify-full"}


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def merged_env(path: Path) -> dict[str, str]:
    values = parse_env_file(path)
    for key, value in os.environ.items():
        if key in values and value:
            values[key] = value
    return values


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return not value or any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def truthy(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def validate(values: dict[str, str], allow_staging: bool = False) -> tuple[list[str], list[str], dict[str, str]]:
    errors: list[str] = []
    warnings: list[str] = []
    facts: dict[str, str] = {}

    required = (
        "DATABASE_URL",
        "PG_DUMP_DATABASE_URL",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_BACKUP_BUCKET",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "TLS_EMAIL",
        "AUTOMATION_SERVICE_KEY",
        "N8N_ENCRYPTION_KEY",
    )
    for key in required:
        value = values.get(key, "").strip()
        if is_placeholder(value):
            errors.append(f"{key} is missing or still a placeholder")

    app_env = values.get("APP_ENV", "").strip().lower()
    if allow_staging:
        if app_env not in {"staging", "production"}:
            errors.append("APP_ENV must be staging or production")
    elif app_env != "production":
        errors.append("APP_ENV must be production")

    if not truthy(values.get("COOKIE_SECURE", "")):
        errors.append("COOKIE_SECURE must be true for external HTTPS")
    if not truthy(values.get("REQUIRE_MIGRATION_HISTORY", "")):
        errors.append("REQUIRE_MIGRATION_HISTORY must be true")
    if not truthy(values.get("REQUIRE_RECENT_BACKUP", "")):
        errors.append("REQUIRE_RECENT_BACKUP must be true")
    if not truthy(values.get("OFFSITE_BACKUP_REQUIRED", "")):
        errors.append("OFFSITE_BACKUP_REQUIRED must be true for autonomous Beget operation")
    if values.get("DB_BACKUP_MODE", "").strip() != "url":
        errors.append("DB_BACKUP_MODE must be url for managed PostgreSQL DBaaS")

    database_url = values.get("DATABASE_URL", "").strip()
    dump_url = values.get("PG_DUMP_DATABASE_URL", "").strip()
    db_parts = dump_parts = None
    for label, value in (("DATABASE_URL", database_url), ("PG_DUMP_DATABASE_URL", dump_url)):
        if not value:
            continue
        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            errors.append(f"{label} is invalid: {exc}")
            continue
        if parsed.scheme not in {"postgres", "postgresql"}:
            errors.append(f"{label} must use PostgreSQL")
        if not parsed.hostname or parsed.hostname in {"localhost", "127.0.0.1", "::1", "postgres"}:
            errors.append(f"{label} must point to the external/private managed DB endpoint")
        query = parse_qs(parsed.query)
        sslmode = (query.get("sslmode") or [""])[0].lower()
        if sslmode not in TLS_SSLMODES:
            errors.append(f"{label} must explicitly use sslmode=require, verify-ca or verify-full")
        if label == "PG_DUMP_DATABASE_URL" and "schema" in query:
            errors.append("PG_DUMP_DATABASE_URL must not contain Prisma-only schema=")
        facts[f"{label.lower()}_host"] = parsed.hostname or ""
        facts[f"{label.lower()}_port"] = str(parsed.port or 5432)
        if label == "DATABASE_URL":
            db_parts = parsed
        else:
            dump_parts = parsed

    if db_parts and dump_parts:
        if (db_parts.hostname, db_parts.port or 5432, db_parts.path) != (
            dump_parts.hostname,
            dump_parts.port or 5432,
            dump_parts.path,
        ):
            errors.append("DATABASE_URL and PG_DUMP_DATABASE_URL must target the same host/port/database")

    s3_endpoint = values.get("S3_ENDPOINT_URL", "").strip()
    if s3_endpoint:
        try:
            s3_parts = urlsplit(s3_endpoint)
            if s3_parts.scheme != "https" or not s3_parts.hostname:
                errors.append("S3_ENDPOINT_URL must be an HTTPS endpoint")
            if s3_parts.query or s3_parts.fragment:
                errors.append("S3_ENDPOINT_URL must not contain query/fragment")
            facts["s3_host"] = s3_parts.hostname or ""
        except ValueError as exc:
            errors.append(f"S3_ENDPOINT_URL is invalid: {exc}")

    for key in ("PUBLIC_HOST", "ADMIN_HOST", "STAFF_HOST", "API_HOST", "AUTOMATION_HOST"):
        host = values.get(key, "").strip().lower()
        if not host:
            errors.append(f"{key} is required")
            continue
        if not allow_staging and "staging" in host:
            errors.append(f"{key} contains staging in production environment")
        facts[key.lower()] = host

    service_key = values.get("AUTOMATION_SERVICE_KEY", "")
    if service_key and len(service_key) < 32:
        errors.append("AUTOMATION_SERVICE_KEY must be at least 32 characters")
    encryption_key = values.get("N8N_ENCRYPTION_KEY", "")
    if encryption_key and len(encryption_key) < 32:
        errors.append("N8N_ENCRYPTION_KEY must be at least 32 characters")
    if service_key and encryption_key and service_key == encryption_key:
        errors.append("AUTOMATION_SERVICE_KEY and N8N_ENCRYPTION_KEY must be different secrets")

    if values.get("TELEGRAM_SALES_BOT_TOKEN") and not values.get("TELEGRAM_SALES_WEBHOOK_SECRET"):
        errors.append("Telegram Sales is enabled without TELEGRAM_SALES_WEBHOOK_SECRET")
    if values.get("GREEN_API_ID_INSTANCE") or values.get("GREEN_API_TOKEN_INSTANCE"):
        if not values.get("GREEN_API_ID_INSTANCE") or not values.get("GREEN_API_TOKEN_INSTANCE"):
            errors.append("GREEN API credentials are partially configured")
        if not values.get("GREEN_API_WEBHOOK_SECRET"):
            errors.append("GREEN API is enabled without GREEN_API_WEBHOOK_SECRET")

    if not values.get("LAST_VERIFIED_BACKUP_AT", "").strip():
        warnings.append("LAST_VERIFIED_BACKUP_AT is empty; expected before final production GO, but may be empty before first staging restore rehearsal")

    return errors, warnings, facts


def network_checks(values: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    errors: list[str] = []
    facts: dict[str, str] = {}

    parsed = urlsplit(values["DATABASE_URL"])
    host = parsed.hostname or ""
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=8):
            facts["database_tcp"] = "reachable"
    except OSError as exc:
        errors.append(f"DBaaS TCP reachability failed for {host}:{port}: {exc.__class__.__name__}")

    s3_url = values["S3_ENDPOINT_URL"].rstrip("/") + "/"
    request = urllib.request.Request(s3_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            facts["s3_https"] = f"reachable_http_{response.status}"
    except urllib.error.HTTPError as exc:
        # 401/403/404 from an unauthenticated HEAD still proves DNS/TLS/HTTP reachability.
        if exc.code < 500:
            facts["s3_https"] = f"reachable_http_{exc.code}"
        else:
            errors.append(f"S3 HTTPS endpoint returned server error {exc.code}")
    except Exception as exc:
        errors.append(f"S3 HTTPS reachability failed: {exc.__class__.__name__}")

    return errors, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--network", action="store_true", help="also test DB TCP and S3 HTTPS reachability")
    parser.add_argument("--allow-staging", action="store_true")
    args = parser.parse_args()

    path = Path(args.env_file).resolve()
    if not path.is_file():
        print(f"FAIL: env file not found: {path}")
        return 2
    values = merged_env(path)
    errors, warnings, facts = validate(values, allow_staging=args.allow_staging)

    if args.network and not errors:
        network_errors, network_facts = network_checks(values)
        errors.extend(network_errors)
        facts.update(network_facts)

    print("Three Crowns Beget environment preflight")
    for warning in warnings:
        print(f"WARN: {warning}")
    for key, value in sorted(facts.items()):
        print(f"FACT: {key}={value}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: BLOCKED")
        return 1
    print("RESULT: PASS" + (" WITH NETWORK" if args.network else " STATIC"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
