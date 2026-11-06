#!/usr/bin/env python3
"""One-hotel provider preflight. Read-only, credential-redacted, NEVER live acceptance.

Loads configuration from the *current process environment* only. It never calls a
provider, opens a database, reads arbitrary .env files, or dumps secrets.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

def _valid_https_origin(value: str, allowed_host: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return bool(
        parsed.scheme == "https" and parsed.hostname == allowed_host
        and parsed.netloc == allowed_host and parsed.path in ("", "/")
        and not parsed.query and not parsed.fragment
    )

def readiness(env: dict[str, str]) -> dict[str, object]:
    hotel = env.get("PROPERTY_CODE", "").strip()
    issues = []
    valid_hotel = bool(re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", hotel)) and hotel != "MARINA_DEMO"
    if not valid_hotel:
        issues.append("PROPERTY_CODE_NOT_APPROVED")

    whatsapp_requested = env.get("ENABLE_GREEN_API_CONNECTION") == "true"
    paired = (
        valid_hotel
        and whatsapp_requested
        and env.get("GREEN_API_PROPERTY_CODE") == hotel
        and bool(re.fullmatch(r"[0-9]{6,14}", env.get("GREEN_API_ID_INSTANCE", "")))
        and bool(re.fullmatch(r"[A-Za-z0-9_-]{16,256}", env.get("GREEN_API_TOKEN_INSTANCE", "")))
        and bool(re.fullmatch(r"[A-Za-z0-9_-]{32,256}", env.get("AUTOMATION_SERVICE_KEY", "")))
        and bool(re.fullmatch(r"(?:[a-z0-9-]+\.)?api\.green-?api\.com", (urlsplit(env.get("GREEN_API_URL", "")).hostname or "")))
    )
    if whatsapp_requested:
        if not paired:
            issues.append("WHATSAPP_HOTEL_PAIRING_OR_CREDENTIALS_INVALID")
        if not _valid_https_origin(env.get("GREEN_API_URL", ""), (urlsplit(env.get("GREEN_API_URL", "")).hostname or "")):
            issues.append("WHATSAPP_UNTRUSTED_ORIGIN")
    else:
        issues.append("WHATSAPP_NOT_ENABLED")

    model = (
        env.get("OPENAI_MARINA_ASSISTANT_MODEL")
        or env.get("OPENAI_PUBLIC_ASSISTANT_MODEL")
        or env.get("OPENAI_SALES_MODEL")
        or ""
    )
    key = env.get("OPENAI_API_KEY", "")
    ai_url = env.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    configured_ai = bool(
        key and model and ai_url.endswith("/v1")
        and _valid_https_origin(ai_url.removesuffix("/v1"), "api.openai.com")
    )
    if not configured_ai:
        issues.append("MARINA_AI_PROVIDER_NOT_CONFIGURED")

    # Explicit external acceptance is required. Static config cannot establish
    # actual message delivery, knowledge isolation or human assignment.
    issues.extend(["WHATSAPP_LIVE_DELIVERY_NOT_ACCEPTED", "MARINA_AI_LIVE_HANDOFF_NOT_ACCEPTED"])
    return {
        "component": "marina-single-property-provider-preflight",
        "property_binding": "VALID" if valid_hotel else "BLOCKED",
        "whatsapp_config": "CONFIGURED_NOT_VERIFIED" if paired else "BLOCKED",
        "marina_ai_config": "CONFIGURED_NOT_VERIFIED" if configured_ai else "BLOCKED",
        "whatsapp_live_delivery": "NOT_ACCEPTED",
        "marina_ai_live_handoff": "NOT_ACCEPTED",
        "commercial_status": "NO_GO",
        "blockers": sorted(set(issues)),
    }

if __name__ == "__main__":
    try:
        print(json.dumps(readiness(dict(os.environ)), ensure_ascii=False, sort_keys=True))
        sys.exit(2)
    except Exception:
        # Never include the exception text: configuration could contain secrets.
        print(json.dumps({"component":"marina-single-property-provider-preflight",
                          "commercial_status":"NO_GO",
                          "blockers":["INVALID_PROVIDER_CONFIGURATION"]}))
        sys.exit(2)
