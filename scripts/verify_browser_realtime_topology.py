#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CADDY = (ROOT / "deploy/Caddyfile").read_text(encoding="utf-8")
PROD = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
BEGET = (ROOT / "compose.beget.yaml").read_text(encoding="utf-8")
ENV_PROD = (ROOT / ".env.production.example").read_text(encoding="utf-8")
ENV_BEGET = (ROOT / ".env.beget.example").read_text(encoding="utf-8")

errors: list[str] = []

def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")

# Browser session cookies remain host-only. Do not widen them to the parent domain.
for label, env in (("production env", ENV_PROD), ("Beget env", ENV_BEGET)):
    require(env, "COOKIE_DOMAIN=\n", label)
    if "COOKIE_DOMAIN=.3korony.com" in env or "COOKIE_DOMAIN=3korony.com" in env:
        errors.append(f"{label}: broad cross-subdomain session cookie is forbidden")

# Admin browser WebSocket must be same-origin with the host that owns the admin cookie.
for label, compose in (("production compose", PROD), ("Beget compose", BEGET)):
    require(compose, "NEXT_PUBLIC_CORE_WS_URL: wss://${ADMIN_HOST}", label)
    if "NEXT_PUBLIC_CORE_WS_URL: wss://${API_HOST}" in compose:
        errors.append(f"{label}: cross-subdomain browser WebSocket to API_HOST is forbidden")

admin_marker = "{$ADMIN_HOST:admin.3korony.com} {"
staff_marker = "{$STAFF_HOST:staff.3korony.com} {"
api_marker = "{$API_HOST:api.3korony.com} {"

if admin_marker not in CADDY or staff_marker not in CADDY or api_marker not in CADDY:
    errors.append("Caddyfile: authenticated host blocks are missing")
    admin_block = staff_block = ""
else:
    admin_block = CADDY.split(admin_marker, 1)[1].split(staff_marker, 1)[0]
    staff_block = CADDY.split(staff_marker, 1)[1].split(api_marker, 1)[0]

# /ws/* must be routed to Core before the generic Next.js handler.
for label, block, next_target in (("admin", admin_block, "admin:3001"), ("staff", staff_block, "staff:3002")):
    require(block, "@core_ws path /ws/*", f"Caddy {label}")
    require(block, "handle @core_ws", f"Caddy {label}")
    require(block, "reverse_proxy api:8000", f"Caddy {label}")
    require(block, f"reverse_proxy {next_target}", f"Caddy {label}")
    core_pos = block.find("reverse_proxy api:8000")
    next_pos = block.find(f"reverse_proxy {next_target}")
    if core_pos < 0 or next_pos < 0 or core_pos > next_pos:
        errors.append(f"Caddy {label}: realtime Core route must precede generic Next proxy")

print("Three Crowns browser realtime topology guard")
if errors:
    for error in errors:
        print(f"FAIL: {error}")
    raise SystemExit(1)
print("PASS: host-only sessions and same-origin browser WSS topology are enforced")
