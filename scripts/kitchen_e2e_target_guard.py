"""Kitchen E2E target validator. CI THREE_CROWNS or explicit disposable RC426 only.

Protects a test that creates reservations and guest records directly in PostgreSQL.
Never modifies runtime cookie policy; HTTPS is mandatory for Secure sessions.
"""
from urllib.parse import urlsplit


def validate_target(*, base: str, database_url: str, property_code: str,
                    cookie_secure: bool, rc426_confirm: str | None) -> None:
    origin = urlsplit(base)
    if origin.scheme not in {"https", "http"} or not origin.hostname:
        raise RuntimeError("Kitchen E2E requires an explicit HTTP(S) API address")
    if origin.username or origin.password:
        raise RuntimeError("Kitchen E2E API URL must not contain credentials")
    if cookie_secure and origin.scheme != "https":
        raise RuntimeError("Kitchen E2E Secure-cookie session requires HTTPS; do not disable Secure")
    db = urlsplit(database_url.split("?", 1)[0])
    if db.scheme not in {"postgresql", "postgres"} or not db.hostname or not db.path:
        raise RuntimeError("Kitchen E2E requires a valid PostgreSQL DSN")
    name = db.path.lstrip("/")
    if property_code == "THREE_CROWNS":
        if name != "resort_os" or db.hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError("THREE_CROWNS kitchen CI must use localhost resort_os")
        if origin.hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError("THREE_CROWNS kitchen CI must use localhost API")
    elif property_code == "MARINA_FULL_CI":
        if rc426_confirm != "ISOLATED_RC426_KITCHEN_E2E":
            raise RuntimeError("Explicit RC426 disposable kitchen E2E confirmation required")
        if name != "marina_rc426_accept" or db.hostname != "postgres":
            raise RuntimeError("RC426 kitchen E2E may only mutate disposable marina_rc426_accept")
        if not cookie_secure or origin.scheme != "https":
            raise RuntimeError("RC426 test must retain Secure cookies and HTTPS")
        if not origin.hostname.endswith(".trycloudflare.com"):
            raise RuntimeError("RC426 requires dedicated public test HTTPS tunnel")
    else:
        raise RuntimeError("Kitchen E2E rejects non-synthetic property")