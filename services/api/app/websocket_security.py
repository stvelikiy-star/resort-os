from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import WebSocket

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
_default_enforce = "true" if APP_ENV == "production" else "false"
WS_ENFORCE_SAME_ORIGIN = os.environ.get("WS_ENFORCE_SAME_ORIGIN", _default_enforce).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _expected_origin(websocket: WebSocket) -> str | None:
    host = (websocket.headers.get("host") or "").strip().lower()
    if not host:
        return None
    forwarded_proto = (websocket.headers.get("x-forwarded-proto") or "").split(",", 1)[0].strip().lower()
    if forwarded_proto in {"http", "https"}:
        scheme = forwarded_proto
    else:
        scheme = "https" if websocket.url.scheme == "wss" else "http"
    return f"{scheme}://{host}"


def websocket_origin_allowed(websocket: WebSocket) -> bool:
    """Require browser WebSocket Origin to match the host serving its auth cookie.

    Production Caddy preserves the original Host and forwards X-Forwarded-Proto.
    Host-only session cookies therefore stay isolated to admin/staff while /ws/*
    is proxied to Core on the same browser origin.
    """
    if not WS_ENFORCE_SAME_ORIGIN:
        return True
    raw_origin = (websocket.headers.get("origin") or "").strip()
    expected = _expected_origin(websocket)
    if not raw_origin or not expected:
        return False
    try:
        parsed = urlsplit(raw_origin)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return False
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}" == expected


async def require_websocket_same_origin(websocket: WebSocket) -> bool:
    if websocket_origin_allowed(websocket):
        return True
    await websocket.close(code=4403, reason="WebSocket origin is not allowed")
    return False
