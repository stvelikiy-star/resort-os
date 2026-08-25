import hmac
import os
from typing import Any

from fastapi import Header, HTTPException, status

AUTOMATION_SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY")
AUTOMATION_SERVICE_NAME = os.environ.get("AUTOMATION_SERVICE_NAME", "n8n")


async def require_automation_service(
    x_resort_service_key: str | None = Header(default=None, alias="X-Resort-Service-Key"),
) -> dict[str, Any]:
    if not AUTOMATION_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Automation service authentication is not configured",
        )
    if not x_resort_service_key or not hmac.compare_digest(x_resort_service_key, AUTOMATION_SERVICE_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid automation service credential",
        )
    return {
        "actor_type": "SERVICE",
        "actor_id": AUTOMATION_SERVICE_NAME,
    }
