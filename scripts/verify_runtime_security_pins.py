#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "compose.production.yaml": (
        "image: caddy:2.11.4-alpine",
        "image: postgres:16.15-alpine",
        "n8nio/n8n:2.37.10",
    ),
    "compose.beget.yaml": (
        "image: caddy:2.11.4-alpine",
        "n8nio/n8n:2.37.10",
    ),
    "compose.staging.yaml": (
        "image: postgres:16.15-alpine",
    ),
    ".env.production.example": (
        "N8N_IMAGE=n8nio/n8n:2.37.10",
    ),
    ".env.beget.example": (
        "N8N_IMAGE=n8nio/n8n:2.37.10",
    ),
    "scripts/production_backup.sh": (
        "postgres:16.15-alpine",
    ),
}

FORBIDDEN_ACTIVE = (
    "n8nio/n8n:2.36.2",
    "n8nio/n8n:latest",
    "image: caddy:2-alpine",
    "image: postgres:16-alpine",
    "POSTGRES_CLIENT_IMAGE:-postgres:16-alpine",
)


def main() -> int:
    checked = 0
    texts: dict[str, str] = {}
    for relative, markers in EXPECTED.items():
        path = ROOT / relative
        if not path.exists():
            raise SystemExit(f"RUNTIME_PIN_BLOCKED: missing {relative}")
        text = path.read_text(encoding="utf-8")
        texts[relative] = text
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"RUNTIME_PIN_BLOCKED: {relative} missing {marker}")
            checked += 1

    for relative, text in texts.items():
        for marker in FORBIDDEN_ACTIVE:
            if marker in text:
                raise SystemExit(f"RUNTIME_PIN_BLOCKED: {relative} contains forbidden {marker}")

    package_ci = (ROOT / ".github/workflows/single-server-production-package-ci.yml").read_text(encoding="utf-8")
    for marker in (
        "n8nio/n8n:2.37.10",
        "postgres:16.15-alpine",
        "caddy:2.11.4-alpine",
        "Vulnerable/stale n8n 2.36.2 must not appear",
    ):
        if marker not in package_ci:
            raise SystemExit(f"RUNTIME_PIN_BLOCKED: production package CI missing {marker}")
        checked += 1

    print(f"RUNTIME_SECURITY_PINS_PASS checks={checked}")
    print("BOUNDARY: exact production/staging infrastructure pins; public website source unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
