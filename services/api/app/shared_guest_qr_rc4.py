"""Opt-in RC4 Guest QR admission without mutating frozen RC3 route source.

The same canonical Resort Core application and handlers process every admitted
request; RC3 remains authoritative for every other request/WS path. Staging
permission is deliberately disabled by default.
"""
import os
import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from starlette.responses import JSONResponse

from . import auth, guest_os
from .shared_auth_preview import SharedAuthPreviewBoundary


UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
TOKEN = r"[A-Za-z0-9_-]{16,128}"
ADMIN_QR = re.compile(rf"^/api/v1/admin/guest-os/room-qrs/{UUID}/(?:issue|rotate)$")
GUEST_ROOM = re.compile(rf"^/api/v1/guest-os/rooms/{TOKEN}$")
GUEST_PIN = re.compile(rf"^/api/v1/guest-os/rooms/{TOKEN}/verify$")
GUEST_TASKS = re.compile(rf"^/api/v1/guest-os/rooms/{TOKEN}/requests$")
GUEST_TASK_CANCEL = re.compile(
    rf"^/api/v1/guest-os/rooms/{TOKEN}/requests/{UUID}/cancel$"
)
EXACT = {
    ("GET", "/api/v1/admin/guest-os/room-qrs"),
    ("POST", "/api/v1/guest-os/logout"),
}


def guest_qr_rc4_requested() -> bool:
    return os.environ.get("MARINA_SHARED_GUEST_QR_RC4_ENABLED") == "true"


def guest_qr_rc4_allowed(method: str, path: str) -> bool:
    """Exact reviewed method+path contract, not a prefix allowlist."""
    if (method, path) in EXACT:
        return True
    if method == "POST" and ADMIN_QR.fullmatch(path):
        return True
    if method == "GET" and GUEST_ROOM.fullmatch(path):
        return True
    if method == "POST" and GUEST_PIN.fullmatch(path):
        return True
    if method in {"GET", "POST"} and GUEST_TASKS.fullmatch(path):
        return True
    if method == "POST" and GUEST_TASK_CANCEL.fullmatch(path):
        return True
    # Preflight is valid only where an admitted real method exists. No broad
    # wildcard guest API or implicit AI/finance/provider endpoint exposure.
    return method == "OPTIONS" and any(
        guest_qr_rc4_allowed(m, path) for m in ("GET", "POST")
    )


def guest_qr_rc4_guard() -> None:
    """Fail closed before dispatch on every opt-in Guest OS request."""
    auth.shared_auth_preview_guard()
    if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED:
        raise HTTPException(503, detail="RC4 Guest QR requires shared authentication")
    if os.environ.get("APP_ENV") != "staging":
        raise HTTPException(503, detail="RC4 Guest QR is isolated staging only")
    if os.environ.get("MARINA_SHARED_GUEST_QR_RC4_CONFIRM") != (
        "REVIEWED_SHARED_GUEST_QR_STAGING_ONLY"
    ):
        raise HTTPException(503, detail="RC4 Guest QR staging approval missing")
    if not guest_os.COOKIE_SECURE or not auth.COOKIE_SECURE:
        raise HTTPException(503, detail="RC4 Guest QR requires Secure cookies")
    origin = guest_os.guest_qr_public_origin()
    expected_origin = os.environ.get("MARINA_SHARED_GUEST_QR_RC4_ORIGIN", "").rstrip("/")
    if not expected_origin or expected_origin != origin:
        raise HTTPException(503, detail="RC4 Guest QR origin mismatch")
    # Legacy hotel's domain is not a valid front door for an unrelated
    # multi-property staging installation, even if somebody set it explicitly.
    if urlsplit(origin).hostname in {"3korony.com", "www.3korony.com"}:
        raise HTTPException(503, detail="RC4 Guest QR cannot use legacy hotel origin")


class SharedGuestQrRc4Boundary:
    """Only these new routes use the canonical app. All others use frozen RC3."""

    def __init__(self, app):
        self.app = app
        self.rc3 = SharedAuthPreviewBoundary(app)

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or not guest_qr_rc4_requested()
                or not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED):
            return await self.rc3(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if (not isinstance(method, str) or not isinstance(path, str)
                or not guest_qr_rc4_allowed(method, path)):
            return await self.rc3(scope, receive, send)
        try:
            guest_qr_rc4_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        return await self.app(scope, receive, send)
