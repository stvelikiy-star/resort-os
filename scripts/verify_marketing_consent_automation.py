#!/usr/bin/env python3
from __future__ import annotations

import os
import time

import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY", "ci-marketing-service-key")


def assert_ok(response: httpx.Response, label: str) -> dict:
    if response.status_code >= 400:
        raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text}")
    return response.json()


def audience(client: httpx.Client, key: str | None) -> dict:
    headers = {"X-Resort-Service-Key": key} if key is not None else {}
    return assert_ok(
        client.get("/api/v1/integrations/marketing/audience", params={"channel": "WHATSAPP"}, headers=headers),
        "automation audience",
    )


def main() -> None:
    suffix = str(int(time.time() * 1000))[-9:]
    opted_phone = f"+996555{suffix[-6:]}"
    silent_phone = f"+996700{suffix[-6:]}"

    with httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True) as client:
        no_key = client.get("/api/v1/integrations/marketing/audience", params={"channel": "WHATSAPP"})
        assert no_key.status_code == 401, (no_key.status_code, no_key.text)
        bad_key = client.get(
            "/api/v1/integrations/marketing/audience",
            params={"channel": "WHATSAPP"},
            headers={"X-Resort-Service-Key": "wrong-key"},
        )
        assert bad_key.status_code == 401, (bad_key.status_code, bad_key.text)

        opted = assert_ok(
            client.post(
                "/api/v1/booking/requests",
                json={
                    "guest_name": "Marketing Consent CI",
                    "phone": opted_phone,
                    "check_in": "2026-10-10",
                    "check_out": "2026-10-12",
                    "adults": 2,
                    "children": 0,
                    "source": "CI_MARKETING",
                    "marketing_opt_in": True,
                    "marketing_channels": ["WHATSAPP"],
                    "marketing_policy_version": "ci-2026-09-12",
                    "utm_source": "ci",
                    "utm_medium": "automation",
                    "utm_campaign": "consent-boundary",
                },
            ),
            "opted-in booking request",
        )
        request_id = opted["id"]
        assert opted["marketing_consent_recorded"] is True, opted

        silent = assert_ok(
            client.post(
                "/api/v1/booking/requests",
                json={
                    "guest_name": "No Consent CI",
                    "phone": silent_phone,
                    "check_in": "2026-10-10",
                    "check_out": "2026-10-12",
                    "adults": 1,
                    "children": 0,
                    "source": "CI_MARKETING_NO_CONSENT",
                },
            ),
            "non-consented booking request",
        )
        assert silent["marketing_consent_recorded"] is False, silent

        before = audience(client, SERVICE_KEY)
        assert before["service_authenticated"] is True, before
        by_request = {item["request_id"]: item for item in before["items"]}
        assert request_id in by_request, before
        assert by_request[request_id]["phone"] == opted_phone, by_request[request_id]
        assert by_request[request_id]["utm_campaign"] == "consent-boundary", by_request[request_id]
        assert silent["id"] not in by_request, before

        unsubscribed = assert_ok(
            client.post(
                "/api/v1/integrations/marketing/provider-events",
                headers={"X-Resort-Service-Key": SERVICE_KEY},
                json={
                    "request_id": request_id,
                    "channel": "WHATSAPP",
                    "event_type": "UNSUBSCRIBED",
                    "provider": "CI_PROVIDER",
                    "provider_message_id": f"ci-unsub-{suffix}",
                    "campaign_code": "CONSENT_BOUNDARY_CI",
                },
            ),
            "provider unsubscribe",
        )
        assert unsubscribed["opted_out"] is True, unsubscribed
        assert unsubscribed["consent_id"], unsubscribed

        after = audience(client, SERVICE_KEY)
        remaining_request_ids = {item["request_id"] for item in after["items"]}
        assert request_id not in remaining_request_ids, after

    print("PASS: service audience rejects missing and invalid credentials")
    print("PASS: explicit WHATSAPP opt-in enters automation audience")
    print("PASS: no-consent booking request never enters automation audience")
    print("PASS: provider UNSUBSCRIBED records opt-out and immediately removes contact")


if __name__ == "__main__":
    main()
