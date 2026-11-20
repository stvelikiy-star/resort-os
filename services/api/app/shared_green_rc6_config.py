"""Hotel-specific GreenAPI QR provisioning in isolated shared staging only.

Provider access stays owner-only and read/QR-only. Credentials come exclusively
from server deployment secrets, NEVER from HTTP headers, URLs or other hotels.
"""
import json
import os
import re
import uuid

from fastapi import HTTPException

from . import auth


def shared_green_rc6_config(user: dict) -> tuple[str, str, str]:
    auth.shared_auth_preview_guard()
    if (not auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED
            or os.environ.get("APP_ENV") != "staging"
            or os.environ.get("MARINA_SHARED_GUEST_QR_RC4_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_INBOX_RC5_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_RC6_ENABLED") != "true"
            or os.environ.get("MARINA_SHARED_GREEN_RC6_CONFIRM") != (
                "REVIEWED_SHARED_GREEN_QR_STAGING_ONLY"
            )):
        raise HTTPException(503, detail="Shared WhatsApp QR pairing is not enabled")

    try:
        rows = json.loads(os.environ.get("MARINA_SHARED_GREEN_RC6_CONFIG_JSON", ""))
        if not isinstance(rows, list) or not 2 <= len(rows) <= 100:
            raise ValueError("Not a reviewed multi-hotel provider map")
        validated = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "tenant_id", "property_id", "property_code",
                "provider_origin", "instance", "token",
            }:
                raise ValueError("Unknown provider config keys")
            if any(not isinstance(value, str) for value in row.values()):
                raise ValueError("Invalid provider fields")
            parsed = {k: str(uuid.UUID(row[k])) for k in ("tenant_id", "property_id")}
            if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,79}", row["property_code"])
                    or row["property_code"] in {"MARINA_DEMO", "MARINA_HOTEL01"}
                    or not re.fullmatch(r"[0-9]{5,24}", row["instance"])
                    or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", row["token"])):
                raise ValueError("Invalid provider config values")
            validated.append({**row, **parsed})
        for field in ("property_id", "instance", "token"):
            if len(set(row[field] for row in validated)) != len(validated):
                raise ValueError("Duplicate provider binding")
        match = [
            row for row in validated
            if row["property_id"] == str(uuid.UUID(str(user.get("property_id"))))
            and row["tenant_id"] == str(uuid.UUID(str(user.get("tenant_id"))))
            and row["property_code"] == user.get("property_code")
        ]
        if len(match) != 1:
            raise ValueError("No provider bound to authenticated hotel")
        row = match[0]
        return row["provider_origin"].rstrip("/"), row["instance"], row["token"]
    except (ValueError, TypeError, AttributeError):
        # Never reveal other hotel names, provider account, tokens or bindings.
        raise HTTPException(503, detail="Shared WhatsApp hotel pairing is not configured") from None
