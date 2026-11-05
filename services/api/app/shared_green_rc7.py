"""Strict GREEN-API webhook admission, layered on RC6/RC5/RC4/frozen RC3.

There is exactly one provider-adapter endpoint, not a second Inbox API.
No callback from an unreviewed environment reaches any application handler.
"""
import os

from fastapi import HTTPException
from starlette.responses import JSONResponse

from .shared_green_rc6 import SharedGreenQrRc6Boundary, rc6_guard
from .green_api_webhook import _webhook_bindings

WEBHOOK = "/api/v1/automation/green-api/webhook"


def green_rc7_allowed(method: str, path: str) -> bool:
    return method == "POST" and path == WEBHOOK


def rc7_guard() -> None:
    rc6_guard()
    if (os.environ.get("MARINA_SHARED_GREEN_RC7_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_RC7_CONFIRM") != (
                "REVIEWED_SHARED_GREEN_WEBHOOK_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="GREEN-API shared webhook stage not approved")
    _webhook_bindings()


class SharedGreenWebhookRc7Boundary:
    def __init__(self, app):
        self.app = app
        self.rc6 = SharedGreenQrRc6Boundary(app)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.rc6(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if not isinstance(method, str) or not isinstance(path, str) or not green_rc7_allowed(method, path):
            return await self.rc6(scope, receive, send)
        try:
            rc7_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code,
            )(scope, receive, send)
        return await self.app(scope, receive, send)
