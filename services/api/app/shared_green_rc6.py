"""Owner-only GreenAPI QR status/pairing admission on top of RC5/RC4/RC3.

No send-text, provider callbacks, webhook writes or AI auto-send admitted.
"""
import os

from fastapi import HTTPException
from starlette.responses import JSONResponse

from .shared_inbox_rc5 import SharedInboxRc5Boundary, rc5_guard


EXACT = {
    ("GET", "/api/v1/admin/whatsapp/connection"),
    ("POST", "/api/v1/admin/whatsapp/connection/qr"),
}


def green_rc6_allowed(method: str, path: str) -> bool:
    if (method, path) in EXACT:
        return True
    return method == "OPTIONS" and path in {p for _, p in EXACT}


def rc6_guard() -> None:
    rc5_guard()
    if (os.environ.get("MARINA_SHARED_GREEN_RC6_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_RC6_CONFIRM") != (
                "REVIEWED_SHARED_GREEN_QR_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="Shared WhatsApp QR stage not approved")


class SharedGreenQrRc6Boundary:
    def __init__(self, app):
        self.app = app
        self.rc5 = SharedInboxRc5Boundary(app)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.rc5(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if (not isinstance(method, str) or not isinstance(path, str)
                or not green_rc6_allowed(method, path)):
            return await self.rc5(scope, receive, send)
        try:
            rc6_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        return await self.app(scope, receive, send)
