import asyncio
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.responses import JSONResponse

_WINDOW_SECONDS = 10 * 60
_MAX_ATTEMPTS = 8
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    host = forwarded or (request.client.host if request.client else "unknown")
    return host[:128]


def install_guest_activation_guard(app) -> None:
    """Protect the six-digit guest PIN activation endpoint on the single Core instance.

    The QR activation token is high-entropy and one-time. This guard additionally
    limits repeated PIN attempts per client address. Production is a single API
    service; if Core becomes multi-instance, move this counter to Redis/Postgres.
    """

    @app.middleware("http")
    async def guest_activation_guard(request: Request, call_next):
        if request.method != "POST" or request.url.path != "/api/v1/guest/activate":
            return await call_next(request)

        key = _client_key(request)
        now = time.monotonic()
        async with _lock:
            bucket = _attempts[key]
            while bucket and now - bucket[0] > _WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= _MAX_ATTEMPTS:
                retry_after = max(1, int(_WINDOW_SECONDS - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many guest activation attempts"},
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

        response = await call_next(request)
        if 200 <= response.status_code < 300:
            async with _lock:
                _attempts.pop(key, None)
        return response
