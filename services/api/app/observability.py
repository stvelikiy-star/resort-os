import json
import logging
import re
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request

LOGGER = logging.getLogger("resort.request")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def _request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


def install_observability(app: FastAPI) -> None:
    """Install privacy-conscious request logging.

    Intentionally logs no query string, request/response body, authorization,
    cookies, guest contact data, message text or provider credentials.
    """

    @app.middleware("http")
    async def request_observability(request: Request, call_next: Callable):
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            LOGGER.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": duration_ms,
                    },
                    separators=(",", ":"),
                )
            )
