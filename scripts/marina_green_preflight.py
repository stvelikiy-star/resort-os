#!/usr/bin/env python3
"""Read-only GREEN-API pilot preflight. Never sends messages or changes settings.

Run in the hotel's private server environment. Prints only check booleans.
Required: PROPERTY_CODE, GREEN_API_PROPERTY_CODE, GREEN_API_URL,
GREEN_API_ID_INSTANCE, GREEN_API_TOKEN_INSTANCE, GREEN_API_EXPECTED_PHONE
(E.164 with +), GREEN_API_EXPECTED_WEBHOOK_URL and GREEN_API_WEBHOOK_TOKEN
(raw independent callback secret; not the API token). No secrets as CLI args.
"""
import hmac
import json
import os
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def configuration(env):
    code = env.get("PROPERTY_CODE", "")
    if not code or code == "MARINA_DEMO" or code != env.get("GREEN_API_PROPERTY_CODE"):
        raise ValueError("property binding")
    if env.get("MARINA_TENANT_CONTEXT_ENABLED", "").lower() in ("true", "1", "yes", "on"):
        raise ValueError("single-property preflight only")
    origin = env.get("GREEN_API_URL", "").rstrip("/")
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or parsed.netloc != parsed.hostname
            or parsed.path or parsed.query or parsed.fragment
            or not re.fullmatch(r"(?:[a-z0-9-]+\.)?api\.green-?api\.com", parsed.hostname or "")):
        raise ValueError("provider origin")
    instance = env.get("GREEN_API_ID_INSTANCE", "")
    token = env.get("GREEN_API_TOKEN_INSTANCE", "")
    callback_token = env.get("GREEN_API_WEBHOOK_TOKEN", "")
    phone = env.get("GREEN_API_EXPECTED_PHONE", "")
    webhook = env.get("GREEN_API_EXPECTED_WEBHOOK_URL", "")
    url = urlsplit(webhook)
    if (not re.fullmatch(r"[0-9]{5,24}", instance)
            or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", token)
            or not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", callback_token)
            or hmac.compare_digest(token, callback_token)
            or not re.fullmatch(r"\+[1-9][0-9]{5,14}", phone)
            or url.scheme != "https" or not url.hostname or url.username
            or url.password or url.query or url.fragment
            or url.path != "/api/v1/automation/green-api/webhook"):
        raise ValueError("private settings")
    return origin, instance, token, callback_token, phone[1:] + "@c.us", webhook


def read_provider(config, method):
    if method not in ("getStateInstance", "getSettings"):
        raise ValueError("read-only methods")
    origin, instance, token, *_ = config
    opener = build_opener(ProxyHandler({}), NoRedirect())
    request = Request(f"{origin}/waInstance{instance}/{method}/{token}",
                      headers={"Accept": "application/json"}, method="GET")
    with opener.open(request, timeout=15) as response:
        data = response.read(1_000_001)
        if response.status != 200 or len(data) > 1_000_000:
            raise ValueError("provider response")
    body = json.loads(data)
    if not isinstance(body, dict):
        raise ValueError("provider response")
    return body


def evaluate(config, state, settings):
    _, _, _, callback_token, wid, webhook = config
    actual_token = settings.get("webhookUrlToken")
    # GREEN-API supports raw token (default Bearer) or explicit Bearer prefix.
    token_ok = isinstance(actual_token, str) and any(
        hmac.compare_digest(actual_token.encode("utf-8"), candidate.encode("ascii"))
        for candidate in (callback_token, "Bearer " + callback_token)
    )
    return {
        "authorized": state.get("stateInstance") == "authorized",
        "expected_phone_matches": settings.get("wid") == wid,
        "webhook_url_matches": settings.get("webhookUrl") == webhook,
        "webhook_credential_matches": token_ok,
        "incoming_enabled": settings.get("incomingWebhook") == "yes",
        "delivery_status_enabled": settings.get("outgoingWebhook") == "yes",
        "messaging_verified": False,
        "ai_auto_send_verified": False,
    }


def main():
    try:
        config = configuration(os.environ)
        result = evaluate(config, read_provider(config, "getStateInstance"),
                          read_provider(config, "getSettings"))
        ready = all(value for key, value in result.items()
                    if key not in ("messaging_verified", "ai_auto_send_verified"))
        print(json.dumps({"provider_configuration_matches": ready, **result}, sort_keys=True))
        return 0 if ready else 2
    except Exception:
        # Never output exception, provider URLs, response bodies, QR or tokens.
        print(json.dumps({"provider_configuration_matches": False,
                          "error": "configuration_or_provider_read_failed"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
