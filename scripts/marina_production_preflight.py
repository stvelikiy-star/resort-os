#!/usr/bin/env python3
"""Fail-closed static configuration check for one isolated MARINA Ubuntu stack."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,39}$")
HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$")
URL_SAFE_SECRET_RE = re.compile(r"^[A-Za-z0-9_-]+$")
CONFIRMATION = "CREATE_ONE_EMPTY_MARINA_PROPERTY"
PLACEHOLDERS = ("change_me", "example.invalid", "example.com", "replace_me")


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
        if key in values and value.strip():
            values[key] = value.strip()
    return values


def placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDERS)


def validate(values: dict[str, str], bootstrap: bool = False, allow_test_hosts: bool = False) -> list[str]:
    errors: list[str] = []

    if values.get("APP_ENV", "").strip().lower() != "production":
        errors.append("APP_ENV must be production for this deployment package")
    if not re.fullmatch(r"[0-9a-f]{40}", values.get("MARINA_RELEASE_SHA", "").strip().lower()):
        errors.append("MARINA_RELEASE_SHA must be the exact 40-character tested Git commit SHA")

    slug = values.get("MARINA_INSTANCE_SLUG", "").strip().lower()
    if not SLUG_RE.fullmatch(slug):
        errors.append("MARINA_INSTANCE_SLUG must be 3-40 lowercase letters, digits or hyphens")

    expected_root = f"/srv/marina-smart/{slug}" if slug else ""
    root = values.get("MARINA_HOST_ROOT", "").strip().rstrip("/")
    data_dir = values.get("MARINA_HOST_DATA_DIR", "").strip().rstrip("/")
    if root != expected_root:
        errors.append("MARINA_HOST_ROOT must be /srv/marina-smart/<MARINA_INSTANCE_SLUG>")
    if data_dir != f"{expected_root}/data":
        errors.append("MARINA_HOST_DATA_DIR must be the isolated <MARINA_HOST_ROOT>/data path")

    hosts = {
        key: values.get(key, "").strip().lower()
        for key in ("MARINA_PUBLIC_HOST", "MARINA_ADMIN_HOST", "MARINA_STAFF_HOST", "MARINA_API_HOST", "MARINA_AUTOMATION_HOST")
    }
    for key, host in hosts.items():
        if not HOST_RE.fullmatch(host):
            errors.append(f"{key} must be a valid lowercase DNS hostname")
        elif not allow_test_hosts and placeholder(host):
            errors.append(f"{key} is still a placeholder/test hostname")
    if len(set(hosts.values())) != len(hosts):
        errors.append("Public, admin, staff, API and automation hostnames must be unique")
    public = hosts["MARINA_PUBLIC_HOST"]
    expected_hosts = {
        "MARINA_ADMIN_HOST": f"admin.{public}" if public else "",
        "MARINA_STAFF_HOST": f"staff.{public}" if public else "",
        "MARINA_API_HOST": f"api.{public}" if public else "",
        "MARINA_AUTOMATION_HOST": f"automation.{public}" if public else "",
    }
    for key, expected in expected_hosts.items():
        if hosts[key] != expected:
            errors.append(f"{key} must be exactly {expected or 'a subdomain of MARINA_PUBLIC_HOST'}")

    tls_email = values.get("TLS_EMAIL", "").strip()
    if placeholder(tls_email) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", tls_email):
        errors.append("TLS_EMAIL must be a real operator email, not a placeholder")

    database = values.get("MARINA_POSTGRES_DB", "").strip().lower()
    if slug and database != f"marina_{slug.replace('-', '_')}":
        errors.append("MARINA_POSTGRES_DB must be marina_<slug> (hyphens converted to underscores)")
    db_password = values.get("MARINA_POSTGRES_PASSWORD", "").strip()
    if len(db_password) < 32 or not URL_SAFE_SECRET_RE.fullmatch(db_password) or placeholder(db_password):
        errors.append("MARINA_POSTGRES_PASSWORD must be a unique 32+ character URL-safe secret")

    property_code = values.get("PROPERTY_CODE", "").strip().upper()
    if not CODE_RE.fullmatch(property_code) or placeholder(property_code):
        errors.append("PROPERTY_CODE must be a real 3-40 character uppercase code")
    if placeholder(values.get("MARINA_PROPERTY_NAME", "")):
        errors.append("MARINA_PROPERTY_NAME is required")
    elif len(values["MARINA_PROPERTY_NAME"].strip()) > 160:
        errors.append("MARINA_PROPERTY_NAME must be at most 160 characters")
    tenant_code = values.get("MARINA_TENANT_CODE", "").strip().lower()
    if slug and tenant_code != f"tenant_{slug.replace('-', '_')}":
        errors.append("MARINA_TENANT_CODE must be tenant_<slug> (hyphens converted to underscores)")
    if values.get("MARINA_TENANT_CONTEXT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}:
        errors.append("MARINA_TENANT_CONTEXT_ENABLED must remain false for one-database-per-hotel isolation")
    timezone = values.get("MARINA_TIMEZONE", "Asia/Bishkek").strip()
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        errors.append("MARINA_TIMEZONE must be a valid IANA timezone")
    if not re.fullmatch(r"[A-Z]{3}", values.get("MARINA_CURRENCY", "KGS").strip().upper()):
        errors.append("MARINA_CURRENCY must be a three-letter code")
    if not CODE_RE.fullmatch(values.get("RATE_PLAN_CODE", "").strip().upper()):
        errors.append("RATE_PLAN_CODE must be 3-40 uppercase letters, digits, _ or -")

    for key in ("AUTOMATION_SERVICE_KEY", "N8N_ENCRYPTION_KEY"):
        secret = values.get(key, "").strip()
        if len(secret) < 32 or placeholder(secret):
            errors.append(f"{key} must be a separately generated 32+ character secret")
    if values.get("AUTOMATION_SERVICE_KEY") == values.get("N8N_ENCRYPTION_KEY"):
        errors.append("AUTOMATION_SERVICE_KEY and N8N_ENCRYPTION_KEY must differ")
    if values.get("N8N_IMAGE", "n8nio/n8n:2.37.10").strip() != "n8nio/n8n:2.37.10":
        errors.append("N8N_IMAGE must remain pinned to the audited n8nio/n8n:2.37.10 image")

    if bootstrap:
        if values.get("MARINA_PROVISION_CONFIRM", "").strip() != CONFIRMATION:
            errors.append(f"MARINA_PROVISION_CONFIRM must equal {CONFIRMATION}")
        username = values.get("MARINA_OWNER_USERNAME", "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", username):
            errors.append("MARINA_OWNER_USERNAME must be 3-80 lowercase letters, digits, ., _ or -")
        password = values.get("MARINA_OWNER_PASSWORD", "")
        if not 16 <= len(password) <= 256:
            errors.append("MARINA_OWNER_PASSWORD must be 16-256 characters")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.marina-production")
    parser.add_argument("--bootstrap", action="store_true", help="require first-owner secret and one-shot confirmation")
    parser.add_argument("--allow-test-hosts", action="store_true", help="permit .invalid names for CI only")
    args = parser.parse_args()
    path = Path(args.env_file)
    if not path.is_file():
        print(f"FAIL: env file not found: {path}")
        return 2
    errors = validate(merged_env(path), bootstrap=args.bootstrap, allow_test_hosts=args.allow_test_hosts)
    print("MARINA SMART isolated Ubuntu deployment preflight")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: BLOCKED")
        return 1
    print("PASS: one-hotel paths, DNS, database and secrets satisfy the static deployment contract")
    if args.bootstrap:
        print("PASS: one-shot empty-property confirmation and first-owner credentials are present")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
