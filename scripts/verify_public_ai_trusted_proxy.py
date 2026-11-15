#!/usr/bin/env python3
"""Regression: spoofed X-Forwarded-For must not bypass public AI throttling."""
import sys
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))

from fastapi import HTTPException, Request
from app import auth, public_ai_admin as ai


def request(forwarded="", direct="198.51.100.8"):
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode("ascii")))
    scope = {
        "type": "http", "http_version": "1.1", "method": "POST",
        "path": "/api/v1/public/ai-admin/chat", "query_string": b"",
        "headers": headers, "client": (direct, 12345),
        "server": ("example.test", 443), "scheme": "https",
    }
    return Request(scope)


# Untrusted proxy headers must not partition a single attacker's IP bucket.
with patch.object(auth, "AUTH_TRUST_PROXY_HEADERS", False), patch.object(ai, "AI_ADMIN_RATE_LIMIT_PER_MINUTE", 2):
    ai._rate_windows.clear()
    assert ai._client_key(request("203.0.113.10")) == "198.51.100.8"
    ai._enforce_rate_limit(request("203.0.113.10"))
    ai._enforce_rate_limit(request("203.0.113.11"))
    try:
        ai._enforce_rate_limit(request("203.0.113.12"))
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("Spoofed forwarded header bypassed public AI rate limit")
    # Different genuine direct peers keep independent buckets.
    ai._enforce_rate_limit(request("203.0.113.12", direct="198.51.100.9"))

# Proxy trust only after infrastructure explicitly enables the existing auth flag.
with patch.object(auth, "AUTH_TRUST_PROXY_HEADERS", True):
    assert ai._client_key(request("203.0.113.42, 10.0.0.1")) == "203.0.113.42"
    assert ai._client_key(request("spoofed-by-client")) == "198.51.100.8"
    assert ai._client_key(request("203.0.113.42", direct="198.51.100.10")) == "203.0.113.42"

ai._rate_windows.clear()
print("PUBLIC_AI_TRUSTED_PROXY_NEGATIVE_RATE_LIMIT_PASS")
