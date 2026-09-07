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

# Browser session cookies remain host-only. We deliberately do not widen them to .3korony.com.
for label, env in (("production env", ENV_PROD), ("Beget env", ENV_BEGET)):
    require(env, "COOKIE_DOMAIN=\n", label)
    if "COOKIE_DOMAIN=.3korony.com" in env or "COOKIE_DOMAIN=3korony.com" in env:
        errors.append(f"{label}: broad cross-subdomain session cookie is forbidden")

# Admin WebSocket must be same-origin with the host that owns the admin session cookie.
for label, compose in (("production compose", PROD), ("Beget compose", BEGET)):
    require(compose, "NEXT_PUBLIC_CORE_WS_URL: wss://${ADMIN_HOST}", label)
    if "NEXT_PUBLIC_CORE_WS_URL: wss://${API_HOST}" in compose:
        errors.append(f"{label}: cross-subdomain browser WebSocket to API_HOST is forbidden")

# Caddy must proxy websocket paths on both authenticated browser hosts directly to Core.
for host in ("{$ADMIN_HOST:admin.3korony.com}", "{$STAFF_HOST:staff.3korony.com}"):
    require(CADDY, host, "Caddyfile")

# These exact route fragments ensure /ws/* is handled by Core before the generic Next proxy.
admin_block = CADDY.split("{$ADMIN_HOST:admin.3korony.com} {", 1)[1].split("}", 1)[0] if "{$ADMIN_HOST:admin.3korony.com} {" in CADDY else ""
staff_block = CADDY.split("{$STAFF_HOST:staff.3korony.com} {", 1)[1].split("}", 1)[0] if "{$STAFF_HOST:staff.3korony.com} {" in CADDY else ""
for label, block, next_target in (("admin", admin_block, "admin:3001"), ("staff", staff_block, "staff:3002")):
    require(block, "@realtime path /ws/*", f"Caddy {label}")
    require(block, "reverse_proxy api:8000", f"Caddy {label}")
    require(block, f"reverse_proxy {next_target}", f"Caddy {label}")
    if block.find("reverse_proxy api:8000") > block.find(f"reverse_proxy {next_target}"):
        errors.append(f"Caddy {label}: realtime route must be evaluated before generic Next proxy")

print("Three Crowns browser realtime topology guard")
if errors:
    for error in errors:
        print(f"FAIL: {error}")
    raise SystemExit(1)
print("PASS: host-only sessions and same-origin browser WSS topology are enforced")
