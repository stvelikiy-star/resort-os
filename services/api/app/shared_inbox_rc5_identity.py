"""RC5 inbound-channel identity: hotel is selected by a private adapter key.

No request-provided hotel code, IP address or Green API account may select the
tenant. Legacy single-hotel service authentication is retained unchanged.
No external provider credentials are required or stored in the database.
"""
import hmac
import json
import os
import re
from typing import Any

from fastapi import Header, HTTPException

from . import auth
from .service_auth import require_automation_service


def shared_inbox_rc5_enabled() -> bool:
    return (
        auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED
        and os.environ.get("MARINA_SHARED_INBOX_RC5_ENABLED") == "true"
    )


def configured_channel_adapters() -> tuple[dict[str, str], ...]:
    """Fail-closed multi-hotel adapter registry. Use deployment secrets only."""
    raw = os.environ.get("MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON", "")
    try:
        value = json.loads(raw)
        if not isinstance(value, list) or len(value) < 2 or len(value) > 100:
            raise ValueError("Expected at least two independently bound adapters")
        result = []
        for entry in value:
            if not isinstance(entry, dict) or set(entry) != {
                "tenant_code", "property_code", "channel_code",
                "external_account_id", "service_key",
            }:
                raise ValueError("Invalid adapter fields")
            if not all(isinstance(v, str) for v in entry.values()):
                raise ValueError("Adapter fields must be strings")
            if not (re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,79}", entry["tenant_code"])
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,79}", entry["property_code"])
                    and re.fullmatch(r"[A-Z][A-Z0-9_-]{1,79}", entry["channel_code"])
                    and re.fullmatch(r"[0-9]{5,24}", entry["external_account_id"])
                    and re.fullmatch(r"[A-Za-z0-9_-]{32,256}", entry["service_key"])):
                raise ValueError("Invalid adapter configuration")
            result.append(entry)
        for field in ("property_code", "external_account_id", "service_key"):
            if len({row[field] for row in result}) != len(result):
                raise ValueError("Ambiguous adapter identity")
        if len({(row["tenant_code"], row["property_code"]) for row in result}) != len(result):
            raise ValueError("Ambiguous tenant/property identity")
        return tuple(result)
    except (ValueError, TypeError):
        raise HTTPException(503, detail="Shared Inbox adapters are not configured") from None


def rc5_service_config_guard() -> tuple[dict[str, str], ...]:
    auth.shared_auth_preview_guard()
    if not shared_inbox_rc5_enabled():
        raise HTTPException(503, detail="Shared Inbox is not enabled")
    if os.environ.get("APP_ENV") != "staging":
        raise HTTPException(503, detail="Shared Inbox requires isolated staging")
    if os.environ.get("MARINA_SHARED_INBOX_RC5_CONFIRM") != "REVIEWED_SHARED_INBOX_STAGING_ONLY":
        raise HTTPException(503, detail="Shared Inbox staging approval missing")
    return configured_channel_adapters()


async def require_hotel_channel_service(
    x_resort_service_key: str | None = Header(default=None, alias="X-Resort-Service-Key"),
) -> dict[str, Any]:
    """Exactly one credential maps to one hotel and one WhatsApp instance."""
    if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED:
        return await require_automation_service(x_resort_service_key)
    configs = rc5_service_config_guard()
    if not x_resort_service_key:
        raise HTTPException(401, detail="Invalid automation service credential")
    matches = [row for row in configs if hmac.compare_digest(
        x_resort_service_key, row["service_key"]
    )]
    if len(matches) != 1:
        raise HTTPException(401, detail="Invalid automation service credential")
    entry = matches[0]
    return {
        "actor_type": "SERVICE",
        "actor_id": "shared-inbox:" + entry["property_code"],
        "tenant_code": entry["tenant_code"],
        "property_code": entry["property_code"],
        "channel_code": entry["channel_code"],
        "external_account_id": entry["external_account_id"],
    }


def require_bound_channel(payload: Any, service: dict[str, Any]) -> None:
    """Reject misleading channel and provider-instance IDs even with a valid key."""
    if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED:
        return
    if (payload.channel_kind != "WHATSAPP"
            or payload.channel_code.strip().upper() != service.get("channel_code")
            or payload.external_account_id != service.get("external_account_id")):
        raise HTTPException(403, detail="Channel is not bound to this hotel adapter")


async def resolve_channel_property(conn, service: dict[str, Any]):
    if not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED:
        return await conn.fetchval(
            "SELECT id FROM properties WHERE code=$1",
            os.environ.get("PROPERTY_CODE", "THREE_CROWNS"),
        )
    return await conn.fetchval(
        """SELECT p.id FROM properties p
           JOIN tenants t ON t.id=p."tenantId"
           WHERE p.code=$1 AND t.code=$2 AND t.status='ACTIVE'""",
        service["property_code"], service["tenant_code"],
    )
