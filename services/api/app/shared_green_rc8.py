"""RC8: only explicitly human-initiated WhatsApp sends; no AI auto-send.

Layers on reviewed RC7→RC6→RC5→RC4→immutable RC3.
"""
import os
import re

from fastapi import HTTPException
from starlette.responses import JSONResponse

from .shared_green_rc7 import SharedGreenWebhookRc7Boundary, rc7_guard


UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
HUMAN_SEND = re.compile(rf"^/api/v1/admin/inbox/conversations/{UUID}/send-text$")


def green_rc8_allowed(method: str, path: str) -> bool:
    return method == "POST" and HUMAN_SEND.fullmatch(path) is not None


def rc8_guard() -> None:
    rc7_guard()
    if (os.environ.get("MARINA_SHARED_GREEN_RC8_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_RC8_CONFIRM") != (
                "REVIEWED_HUMAN_WHATSAPP_SEND_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="Human WhatsApp send is not approved")
    if os.environ.get("ENABLE_GREEN_API_CONNECTION") != "true":
        raise HTTPException(503, detail="GREEN-API provider is not configured")


class SharedGreenHumanOutboundRc8Boundary:
    def __init__(self, app):
        self.app = app
        self.rc7 = SharedGreenWebhookRc7Boundary(app)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.rc7(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if (not isinstance(method, str) or not isinstance(path, str)
                or not green_rc8_allowed(method, path)):
            return await self.rc7(scope, receive, send)
        try:
            rc8_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        return await self.app(scope, receive, send)
