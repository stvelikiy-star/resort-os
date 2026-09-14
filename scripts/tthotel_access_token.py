import json
import os
import sys
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = os.environ.get("TTLOCK_API_BASE_URL", "https://euapi.sciener.com").rstrip("/")
CLIENT_ID = os.environ.get("TTLOCK_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("TTHOTEL_CLIENT_SECRET", "").strip()
ACCOUNT = os.environ.get("TTHOTEL_ACCOUNT", "").strip()
PASSWORD = os.environ.get("TTHOTEL_PASSWORD", "").strip()
STATIC_TOKEN = os.environ.get("TTLOCK_ACCESS_TOKEN", "").strip()


def _fail(message: str, *, detail: str | None = None) -> NoReturn:
    print(f"TTHOTEL_AUTH_ERROR: {message}", file=sys.stderr)
    if detail:
        print(detail[:500], file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    # Backward-compatible escape hatch for CI/manual environments.
    if STATIC_TOKEN:
        print(STATIC_TOKEN)
        return

    missing = [
        name
        for name, value in (
            ("TTLOCK_CLIENT_ID", CLIENT_ID),
            ("TTHOTEL_CLIENT_SECRET", CLIENT_SECRET),
            ("TTHOTEL_ACCOUNT", ACCOUNT),
            ("TTHOTEL_PASSWORD", PASSWORD),
        )
        if not value
    ]
    if missing:
        _fail("missing runtime credentials", detail=",".join(missing))

    payload = urlencode(
        {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": ACCOUNT,
            "password": PASSWORD,
        }
    ).encode("utf-8")
    request = Request(
        f"{API_BASE}/oauth2/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        _fail(f"oauth http {exc.code}", detail=detail)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        _fail("oauth request failed", detail=str(exc))

    token = str(body.get("access_token") or "").strip()
    if not token:
        errcode = body.get("errcode")
        errmsg = body.get("errmsg") or body.get("description") or "missing access_token"
        _fail(f"oauth rejected errcode={errcode}", detail=str(errmsg))

    print(token)


if __name__ == "__main__":
    main()
