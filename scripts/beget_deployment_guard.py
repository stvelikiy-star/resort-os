#!/usr/bin/env python3
"""Static fail-closed guard for the Beget autonomous deployment contract."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.beget.yaml"
ENV = ROOT / ".env.beget.example"
BACKUP = ROOT / "scripts/production_backup.sh"
CADDY = ROOT / "deploy/Caddyfile"


def require(text: str, snippet: str, label: str, errors: list[str]) -> None:
    if snippet not in text:
        errors.append(f"{label}: missing required contract snippet {snippet!r}")


def main() -> int:
    errors: list[str] = []
    for path in (COMPOSE, ENV, BACKUP, CADDY):
        if not path.is_file():
            errors.append(f"missing required Beget deployment file: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    compose = COMPOSE.read_text(encoding="utf-8")
    env = ENV.read_text(encoding="utf-8")
    backup = BACKUP.read_text(encoding="utf-8")
    caddy = CADDY.read_text(encoding="utf-8")

    if "\n  postgres:\n" in compose:
        errors.append("compose.beget.yaml: local postgres service is forbidden in DBaaS topology")
    if '"5432:5432"' in compose or "'5432:5432'" in compose:
        errors.append("compose.beget.yaml: PostgreSQL port must never be published")

    for snippet in (
        "DATABASE_URL: ${DATABASE_URL:?DATABASE_URL must point to private Beget PostgreSQL DBaaS}",
        "restart: unless-stopped",
        "max-size: \"20m\"",
        "max-file: \"5\"",
        "N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS: \"true\"",
        "N8N_DIAGNOSTICS_ENABLED: \"false\"",
        "EXECUTIONS_DATA_PRUNE: \"true\"",
        "http://127.0.0.1:5678/healthz",
        "NEXT_PUBLIC_CORE_WS_URL: wss://${ADMIN_HOST}",
    ):
        require(compose, snippet, "compose.beget.yaml", errors)

    if "NEXT_PUBLIC_CORE_WS_URL: wss://${API_HOST}" in compose:
        errors.append("compose.beget.yaml: browser Admin WebSocket must not cross to API_HOST with host-only auth cookie")

    if caddy.count("@core_ws path /ws/*") != 2:
        errors.append("deploy/Caddyfile: expected exactly two same-origin /ws/* matchers for admin and staff")
    if caddy.count("handle @core_ws") != 2:
        errors.append("deploy/Caddyfile: expected exactly two same-origin websocket proxy handlers")
    if caddy.count("reverse_proxy api:8000") < 3:
        errors.append("deploy/Caddyfile: Core websocket/API proxy routing is incomplete")

    for service in ("caddy", "api", "web", "admin", "staff", "n8n"):
        require(compose, f"  {service}:\n", "compose.beget.yaml", errors)

    for snippet in (
        "DATABASE_URL=postgresql://",
        "?sslmode=require",
        "PG_DUMP_DATABASE_URL=postgresql://",
        "DB_BACKUP_MODE=url",
        "OFFSITE_BACKUP_REQUIRED=true",
        "S3_ENDPOINT_URL=",
        "S3_REGION=",
        "S3_BACKUP_BUCKET=",
        "S3_ACCESS_KEY_ID=",
        "S3_SECRET_ACCESS_KEY=",
        "COOKIE_SECURE=true",
        "REQUIRE_MIGRATION_HISTORY=true",
        "REQUIRE_RECENT_BACKUP=true",
    ):
        require(env, snippet, ".env.beget.example", errors)

    if "POSTGRES_PASSWORD=" in env or "POSTGRES_USER=" in env or "POSTGRES_DB=" in env:
        errors.append(".env.beget.example: local Compose PostgreSQL variables must not define the target DB architecture")

    for snippet in (
        "DB_BACKUP_MODE",
        "PG_DUMP_DATABASE_URL",
        "OFFSITE_BACKUP_REQUIRED",
        "--aws-sigv4",
        "OFFSITE_BACKUP=VERIFIED_UPLOAD",
        "PostgreSQL backup is empty",
    ):
        require(backup, snippet, "scripts/production_backup.sh", errors)

    print("Three Crowns Beget deployment guard")
    print("FACT: target_database=external_managed_postgresql")
    print("FACT: target_offsite_backup=required_s3")
    print("FACT: docker_log_rotation=required")
    print("FACT: n8n_healthcheck=required")
    print("FACT: browser_websocket_topology=same_origin_host_only_cookie")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: BEGET DEPLOYMENT CONTRACT DRIFT")
        return 1

    print("PASS: Beget target remains VPS apps + managed DBaaS + required S3 backup + same-origin browser realtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
