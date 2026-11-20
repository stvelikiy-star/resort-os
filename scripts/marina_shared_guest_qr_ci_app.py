"""Isolated two-hotel Guest OS HTTPS acceptance app — NEVER a deployment entrypoint.

Only canonical authentication, PMS booking, stay and Guest OS routers are composed.
Production app_entry and its fail-closed shared-auth allowlist are untouched.
"""
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI

from marina_shared_live_browser_db import dsn

from app.auth import router as auth_router
from app.db import lifespan as core_lifespan
from app.guest_os import admin_router as guest_admin_router, public_router as guest_public_router
from app.guest_requests import router as guest_requests_router
from app.pms_reservation_create import router as reservation_router
from app.stays import router as stays_router


def verify_disposable_guest_ci() -> None:
    if os.environ.get("MARINA_GUEST_QR_CI_CONFIRM") != "ISOLATED_TWO_HOTEL_GUEST_QR_CI_ONLY":
        raise RuntimeError("Guest QR acceptance app requires explicit disposable CI confirmation")
    dsn()  # Existing stringent localhost/database-name/fixture-password gates.
    url = urlsplit(os.environ.get("GUEST_OS_PUBLIC_BASE_URL", ""))
    if (url.scheme, url.hostname, url.port, url.path, url.query, url.fragment) != (
        "https", "localhost", 18443, "", "", ""
    ):
        raise RuntimeError("Guest QR test origin must be isolated https://localhost:18443")
    if os.environ.get("COOKIE_SECURE") != "true":
        raise RuntimeError("Guest QR HTTPS acceptance requires Secure cookies")


verify_disposable_guest_ci()


@asynccontextmanager
async def acceptance_lifespan(app: FastAPI):
    verify_disposable_guest_ci()
    async with core_lifespan(app):
        yield


app = FastAPI(lifespan=acceptance_lifespan)
# No shared-auth middleware bypass: this is a *separate*, locally bound
# limited-router acceptance app, never the deployed all-module app_entry.
app.include_router(auth_router)
app.include_router(reservation_router)
app.include_router(stays_router)
app.include_router(guest_admin_router)
app.include_router(guest_public_router)
app.include_router(guest_requests_router)
