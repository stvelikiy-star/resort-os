"""RC5 opt-in Inbox admission layered on reviewed RC4 (and frozen RC3).

No new API endpoints: only canonical Inbox, normalized ingress and synthetic-only
AI drafts. Sender account is cryptographically bound to one hotel adapter.
Provider delivery, WhatsApp QR provisioning and automatic AI sending stay 503.
"""
import os
import re

from fastapi import HTTPException
from starlette.responses import JSONResponse

from .shared_guest_qr_rc4 import SharedGuestQrRc4Boundary, guest_qr_rc4_guard
from .shared_inbox_rc5_identity import rc5_service_config_guard


UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"
DETAIL = re.compile(rf"^/api/v1/admin/inbox/conversations/{UUID}$")
CLAIM_NOTE = re.compile(rf"^/api/v1/admin/inbox/conversations/{UUID}/(?:claim|notes)$")
STATUS = re.compile(rf"^/api/v1/admin/inbox/conversations/{UUID}/status$")
AI_DRAFT = re.compile(rf"^/api/v1/admin/inbox/conversations/{UUID}/ai-draft$")
EXACT = {
    ("POST", "/api/v1/automation/inbox/messages"),
    ("GET", "/api/v1/admin/inbox/conversations"),
}


def synthetic_ai_draft_only() -> bool:
    """Real-provider AI release is explicitly OUT OF SCOPE for RC5."""
    return (
        os.environ.get("MARINA_SHARED_INBOX_RC5_AI_MOCK_ENABLED") == "true"
        and os.environ.get("MARINA_SHARED_INBOX_RC5_AI_MOCK_CONFIRM") == (
            "ISOLATED_SYNTHETIC_AI_DRAFT_ONLY"
        )
        and os.environ.get("OPENAI_API_BASE_URL", "").rstrip("/") == (
            "http://127.0.0.1:18081/v1"
        )
    )


def shared_inbox_rc5_allowed(method: str, path: str) -> bool:
    if (method, path) in EXACT:
        return True
    if method == "GET" and DETAIL.fullmatch(path) is not None:
        return True
    if method == "POST" and CLAIM_NOTE.fullmatch(path) is not None:
        return True
    if method == "PATCH" and STATUS.fullmatch(path) is not None:
        return True
    if synthetic_ai_draft_only():
        if method == "GET" and path == "/api/v1/admin/inbox/ai-capabilities":
            return True
        if method == "POST" and AI_DRAFT.fullmatch(path) is not None:
            return True
    return method == "OPTIONS" and any(
        shared_inbox_rc5_allowed(m, path) for m in ("GET", "POST", "PATCH")
    )


def rc5_guard() -> None:
    if os.environ.get("MARINA_SHARED_GUEST_QR_RC4_ENABLED") != "true":
        raise HTTPException(503, detail="RC5 requires reviewed RC4 Guest QR stage")
    # RC5 depends on completed RC4 staging contract. No other environment
    # ever enables these routes, including legacy demo or live production.
    guest_qr_rc4_guard()
    rc5_service_config_guard()


class SharedInboxRc5Boundary:
    def __init__(self, app):
        self.app = app
        self.rc4 = SharedGuestQrRc4Boundary(app)

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http"
                or os.environ.get("MARINA_SHARED_INBOX_RC5_ENABLED") != "true"):
            return await self.rc4(scope, receive, send)
        method, path = scope.get("method"), scope.get("path")
        if (not isinstance(method, str) or not isinstance(path, str)
                or not shared_inbox_rc5_allowed(method, path)):
            return await self.rc4(scope, receive, send)
        try:
            rc5_guard()
        except HTTPException as error:
            return await JSONResponse(
                {"detail": error.detail}, status_code=error.status_code
            )(scope, receive, send)
        return await self.app(scope, receive, send)
