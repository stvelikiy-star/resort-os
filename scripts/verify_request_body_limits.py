#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CADDY = (ROOT / "deploy/Caddyfile").read_text(encoding="utf-8")
MEDIA = (ROOT / "services/api/app/site_media.py").read_text(encoding="utf-8")

errors: list[str] = []

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")

# Application limit remains authoritative for media semantics.
require(MEDIA, "MAX_BYTES = 8 * 1024 * 1024", "site_media.py")
require(MEDIA, "len(body) > MAX_BYTES", "site_media.py")
require(MEDIA, "valid_magic(content_type, body)", "site_media.py")

# Edge limits prevent oversized/chunked bodies from being buffered through Next/Core first.
require(CADDY, "@media_upload path /core/api/v1/admin/site/media", "Caddyfile")
media_section = CADDY.split("@media_upload path /core/api/v1/admin/site/media", 1)[1].split("@core_ws path /ws/*", 1)[0]
require(media_section, "max_size 8MB", "Caddy media upload")

if CADDY.count("max_size 1MB") != 1:
    errors.append("Caddyfile: Telegram webhook limit must be exactly one 1MB rule")
if CADDY.count("max_size 2MB") < 4:
    errors.append("Caddyfile: expected generic 2MB body limits on public/admin/staff/API hosts")
if CADDY.count("max_size 8MB") != 1:
    errors.append("Caddyfile: media upload must have exactly one 8MB edge limit")

print("Three Crowns request body limit guard")
if errors:
    for error in errors:
        print(f"FAIL: {error}")
    raise SystemExit(1)
print("PASS: edge and application body-size limits are aligned")
