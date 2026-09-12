#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY", "ci-marketing-service-key")
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "automation" / "n8n" / "marketing-consent-audience.json"


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


def verify_n8n_contract() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    assert workflow.get("active") is False, "marketing workflow must remain inactive until provider UAT"
    nodes = workflow.get("nodes") or []
    http_nodes = [node for node in nodes if node.get("type") == "n8n-nodes-base.httpRequest"]
    assert len(http_nodes) == 1, "marketing audience workflow must have exactly one HTTP handoff"
    http = http_nodes[0]
    params = http.get("parameters") or {}
    assert "/api/v1/integrations/marketing/audience" in str(params.get("url")), params
    headers = ((params.get("headerParameters") or {}).get("parameters") or [])
    assert any(
        h.get("name") == "X-Resort-Service-Key" and "AUTOMATION_SERVICE_KEY" in str(h.get("value"))
        for h in headers
    ), headers
    forbidden_types = {"n8n-nodes-base.postgres", "n8n-nodes-base.mysql", "n8n-nodes-base.microsoftSql"}
    assert not any(node.get("type") in forbidden_types for node in nodes), "workflow must not write DB directly"
    assert not any("greenApi" in str(node.get("type", "")) or "whatsApp" in str(node.get("type", "")) for node in nodes), (
        "audience handoff must not send messages before provider UAT"
    )


def main() -> None:
    verify_n8n_contract()
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

    print("PASS: inactive n8n audience workflow uses service auth and has no outbound provider node")
    print("PASS: service audience rejects missing and invalid credentials")
    print("PASS: explicit WHATSAPP opt-in enters automation audience")
    print("PASS: no-consent booking request never enters automation audience")
    print("PASS: provider UNSUBSCRIBED records opt-out and immediately removes contact")


if __name__ == "__main__":
    main()
