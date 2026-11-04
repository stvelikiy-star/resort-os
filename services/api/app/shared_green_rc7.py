"""Exact RC7 GREEN-API inbound webhook admission on top of RC6 / RC5 / RC4 / RC3."""
import os

from fastapi import HTTPException
from starlette.responses import JSONResponse

from .shared_green_rc6 import SharedGreenQrRc6Boundary, rc6_guard


def rc7_guard() -> None:
    rc6_guard()
    if (os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_WEBHOOK_RC7_CONFIRM") != (
                "REVIEWED_GREEN_WEBHOOK_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="GREEN-API inbound webhook is not enabled")


class SharedGreenWebhookRc7Boundary:
    def __init__(self, app):
        self.app = app
        self.rc6 = SharedGreenQrRc6Boundary(app)

    async def __call__(self, scope, receive, send):
        if not (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/v1/automation/green-api/webhook"
        ):
            return await self.rc6(scope, receive, send)
        try:
            rc7_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        return await self.app(scope, receive, send)
