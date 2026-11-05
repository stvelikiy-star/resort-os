"""P0 shared COOK/WAITER admission: strictly scoped, staging-only, opt-in.

Use existing canonical kitchen/dining handlers, including DB-derived hotel context,
role checks and module ceilings. Every other route delegates to the reviewed
RC3-RC8 middleware selected by main.py. No guest/public/payment/AI paths opened.
"""
import os
import re

from fastapi import HTTPException
from starlette.responses import JSONResponse

from . import auth


UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
KITCHEN_STATUS = re.compile(rf"^/api/v1/kitchen/orders/{UUID}/status$")
TABLE_RESERVATION = re.compile(rf"^/api/v1/dining/table-reservations/{UUID}$")
WAITER_ASSIGN = re.compile(rf"^/api/v1/dining/orders/{UUID}/waiter$")
EXACT = {
    ("GET", "/api/v1/kitchen/orders"),
    ("GET", "/api/v1/dining/floor"),
    ("GET", "/api/v1/dining/table-reservations"),
    ("POST", "/api/v1/dining/table-reservations"),
}


def allowed(method: str, path: str) -> bool:
    if (method, path) in EXACT:
        return True
    if method == "PATCH":
        return any(pattern.fullmatch(path) is not None for pattern in (
            KITCHEN_STATUS, TABLE_RESERVATION, WAITER_ASSIGN,
        ))
    return method == "OPTIONS" and any(allowed(verb, path) for verb in ("GET", "POST", "PATCH"))


def guard() -> None:
    auth.shared_auth_preview_guard()
    if (not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED
            or os.environ.get("APP_ENV") != "staging"
            or os.environ.get("MARINA_SHARED_DINING_P0_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_DINING_P0_CONFIRM")
                != "REVIEWED_SHARED_DINING_STAGING_ONLY"):
        raise HTTPException(503, detail="Shared dining P0 is not approved for this environment")


class SharedDiningP0Boundary:
    def __init__(self, app, previous_boundary):
        self.app = app
        self.previous = previous_boundary(app)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.previous(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if (not isinstance(method, str) or not isinstance(path, str)
                or not allowed(method, path)):
            return await self.previous(scope, receive, send)
        try:
            guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        # Actual authorization, hotel membership and write validation remain
        # in the original canonical FastAPI endpoint dependencies.
        return await self.app(scope, receive, send)
