"""Owner-only GreenAPI QR provisioning for one explicitly bound hotel runtime."""
import base64
import binascii
import os
import re
import time
import logging
from collections import defaultdict, deque
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

from .auth import require_roles
from .runtime_capabilities import env_flag

router = APIRouter(prefix="/api/v1/admin/whatsapp", tags=["whatsapp-connection"])
owner_access = require_roles("OWNER", module_grant=False)
_windows: dict[str, deque[float]] = defaultdict(deque)
STATES = {"notAuthorized", "authorized", "blocked", "sleepMode", "starting", "yellowCard"}


class _ProviderLogFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        redacted = re.sub(r"(/waInstance\d+/[^/\s]+/)[^/\s'\"?]+", r"\1[REDACTED]", message)
        if redacted != message:
            record.msg, record.args = redacted, ()
        return True


for _logger in ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy"):
    logging.getLogger(_logger).addFilter(_ProviderLogFilter())


def _configuration(user):
    if not env_flag("ENABLE_GREEN_API_CONNECTION", False):
        return None
    bound = os.environ.get("GREEN_API_PROPERTY_CODE", "")
    if (not bound or bound != os.environ.get("PROPERTY_CODE")
            or bound != user.get("property_code")
            or env_flag("MARINA_TENANT_CONTEXT_ENABLED", False)):
        raise HTTPException(503, detail="WhatsApp hotel binding is not configured")
    origin = os.environ.get("GREEN_API_URL", "").rstrip("/")
    instance = os.environ.get("GREEN_API_ID_INSTANCE", "")
    token = os.environ.get("GREEN_API_TOKEN_INSTANCE", "")
    try:
        parsed = urlsplit(origin)
    except ValueError:
        raise HTTPException(503, detail="WhatsApp provider is not configured") from None
    host = parsed.hostname or ""
    # Credentials must only be sent to the documented provider, never to a
    # browser-selected address or an arbitrary redirect target.
    if (parsed.scheme != "https" or parsed.netloc != host or parsed.path
            or parsed.query or parsed.fragment
            or not re.fullmatch(r"(?:[a-z0-9-]+\.)?api\.green-?api\.com", host)
            or not re.fullmatch(r"\d+", instance)
            or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", token)):
        raise HTTPException(503, detail="WhatsApp provider is not configured")
    return origin, instance, token


def _limit(user):
    now = time.monotonic()
    key = str(user["id"])
    window = _windows[key]
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= 30:
        raise HTTPException(429, detail="Wait before checking WhatsApp again", headers={"Retry-After": "60"})
    window.append(now)
    if len(_windows) > 1000:
        for old in [k for k, v in _windows.items() if not v or now - v[-1] >= 60]:
            _windows.pop(old, None)


async def _provider(config, method):
    origin, instance, token = config
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            result = await client.get(f"{origin}/waInstance{instance}/{method}/{token}")
        if result.status_code != 200 or len(result.content) > 1_000_000:
            raise ValueError("Rejected response")
        body = result.json()
        if not isinstance(body, dict):
            raise ValueError("Invalid response")
        return body
    except (httpx.HTTPError, ValueError):
        # Provider URLs contain credentials: never return/log their exception
        # text, response body, settings, or redirect Location.
        raise HTTPException(502, detail="WhatsApp provider is temporarily unavailable") from None


def _private(response):
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"


@router.get("/connection")
async def connection_status(response: Response, user=Depends(owner_access)):
    _private(response)
    config = _configuration(user)
    if config is None:
        return {"configured": False, "state": "disabled", "account_authorized": False,
                "messaging_verified": False, "ai_auto_send": False}
    _limit(user)
    body = await _provider(config, "getStateInstance")
    state = body.get("stateInstance")
    if not isinstance(state, str) or state not in STATES:
        raise HTTPException(502, detail="WhatsApp provider returned an unknown state")
    return {"configured": True, "state": state, "account_authorized": state == "authorized",
            "messaging_verified": False, "ai_auto_send": False}


@router.post("/connection/qr")
async def connection_qr(response: Response, user=Depends(owner_access)):
    _private(response)
    config = _configuration(user)
    if config is None:
        raise HTTPException(503, detail="WhatsApp provider is not configured")
    _limit(user)
    body = await _provider(config, "qr")
    if body.get("type") == "alreadyLogged":
        return {"state": "authorized", "qr_data_url": None, "expires_in_seconds": 0}
    message = body.get("message")
    if body.get("type") != "qrCode" or not isinstance(message, str) or len(message) > 900_000:
        raise HTTPException(502, detail="WhatsApp QR is unavailable; check the connection status")
    try:
        raw = base64.b64decode(message, validate=True)
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Not PNG")
    except (ValueError, binascii.Error):
        raise HTTPException(502, detail="WhatsApp provider returned an invalid QR image") from None
    return {"state": "notAuthorized", "qr_data_url": "data:image/png;base64," + message,
            "expires_in_seconds": 20}
