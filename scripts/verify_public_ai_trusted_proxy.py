#!/usr/bin/env python3
"""Legacy CI entry point: verify trusted forwarding and PostgreSQL throttling."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app import auth, public_ai_admin as ai
from verify_public_ai_rate_limit_e2e import main, request


def verify_forwarding():
    app = SimpleNamespace()
    with patch.object(ai, "AI_ADMIN_TRUSTED_PROXY_CIDRS", "127.0.0.1/32,::1/128"):
        with patch.object(auth, "AUTH_TRUST_PROXY_HEADERS", False):
            for forwarded in ("203.0.113.10", "203.0.113.11", "203.0.113.12"):
                assert ai._client_key(request(app, "198.51.100.8", forwarded)) == "198.51.100.8"
            assert ai._client_key(request(app, "198.51.100.9", "203.0.113.12")) == "198.51.100.9"
            assert ai._client_key(request(app, "127.0.0.1", "203.0.113.42")) == "127.0.0.1"
        with patch.object(auth, "AUTH_TRUST_PROXY_HEADERS", True):
            assert ai._client_key(request(app, "198.51.100.8", "203.0.113.42, 10.0.0.1")) == "198.51.100.8"
            assert ai._client_key(request(app, "198.51.100.10", "203.0.113.42")) == "198.51.100.10"
            assert ai._client_key(request(app, "127.0.0.1", "203.0.113.42, 10.0.0.1")) == "203.0.113.42"
            assert ai._client_key(request(app, "127.0.0.1", "spoofed-by-client")) == "127.0.0.1"
            assert ai._client_key(request(app, "127.0.0.1")) == "127.0.0.1"
            assert ai._client_key(request(app, "::1", "2001:db8::42")) == "2001:db8::42"


if __name__ == "__main__":
    verify_forwarding()
    # The existing verifier uses real disposable PostgreSQL, including
    # concurrent requests, independent IPs, daily budget and hashed audit.
    asyncio.run(main())
    print("PUBLIC_AI_TRUSTED_PROXY_NEGATIVE_RATE_LIMIT_PASS")
