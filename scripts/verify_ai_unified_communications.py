#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_KEY = os.environ["AUTOMATION_SERVICE_KEY"]
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]


def service_client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE,
        headers={"X-Resort-Service-Key": SERVICE_KEY},
        timeout=30.0,
    )


def owner_client() -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30.0)
    response = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    response.raise_for_status()
    return client


def detail_code(response: httpx.Response) -> str | None:
    try:
        detail = response.json().get("detail")
    except Exception:
        return None
    return detail.get("code") if isinstance(detail, dict) else None


def normalized_message(
    *,
    kind: str,
    code: str,
    conversation: str,
    message: str,
    text: str,
    direction: str = "INBOUND",
    delivery: str = "RECEIVED",
) -> dict:
    return {
        "idempotency_key": f"block10:{code}:{message}",
        "channel_code": code,
        "channel_kind": kind,
        "channel_display_name": f"Block 10 {kind}",
        "external_account_id": f"acct-{code.lower()}",
        "external_conversation_id": conversation,
        "external_contact_id": f"contact-{conversation}",
        "contact_name": f"Guest {kind}",
        "contact_phone": "+996700123456",
        "contact_username": f"guest_{kind.lower()}",
        "direction": direction,
        "external_message_id": message,
        "sender_type": "GUEST" if direction == "INBOUND" else "STAFF",
        "sender_external_id": "guest-1" if direction == "INBOUND" else "provider-manager",
        "text": text,
        "content_type": "TEXT",
        "delivery_status": delivery,
        "raw_payload": {"block": 10, "kind": kind, "message": message},
    }


def ingest(service: httpx.Client, payload: dict) -> dict:
    response = service.post("/api/v1/automation/inbox/messages", json=payload)
    response.raise_for_status()
    return response.json()


def conversation(owner: httpx.Client, conversation_id: str) -> dict:
    response = owner.get(f"/api/v1/admin/inbox/conversations/{conversation_id}")
    response.raise_for_status()
    return response.json()


def main() -> None:
    service = service_client()
    owner = owner_client()
    suffix = uuid.uuid4().hex[:10]

    capabilities = service.get("/api/v1/automation/capabilities")
    capabilities.raise_for_status()
    caps = capabilities.json()
    assert caps["orchestrator"] == "n8n"
    assert "POST /api/v1/automation/inbox/messages" in caps["allowed"]
    assert "confirm-payment" in caps["forbidden_for_ai"]
    assert "direct PostgreSQL writes" in caps["forbidden_for_ai"]
    assert "different payload" in caps["idempotency_rule"]
    assert "conversation_id" in caps["handoff_rule"]

    channel_results: dict[str, dict] = {}
    specs = [
        ("WHATSAPP", f"WA_BLOCK10_{suffix}"),
        ("INSTAGRAM", f"IG_BLOCK10_{suffix}"),
        ("TELEGRAM", f"TG_BLOCK10_{suffix}"),
    ]
    for kind, code in specs:
        payload = normalized_message(
            kind=kind,
            code=code,
            conversation=f"{kind.lower()}-conversation-{suffix}",
            message=f"{kind.lower()}-message-{suffix}-1",
            text=f"Need a room from {kind}",
        )
        first = ingest(service, payload)
        assert first["idempotent_replay"] is False
        assert first["direction"] == "INBOUND"
        assert first["counts_as_response"] is False
        replay = ingest(service, payload)
        assert replay["idempotent_replay"] is True
        assert replay["id"] == first["id"]

        changed = dict(payload)
        changed["text"] = "DIFFERENT PAYLOAD MUST NOT REPLAY"
        mismatch = service.post("/api/v1/automation/inbox/messages", json=changed)
        assert mismatch.status_code == 409, mismatch.text
        assert detail_code(mismatch) == "INBOX_IDEMPOTENCY_PAYLOAD_MISMATCH", mismatch.text
        channel_results[kind] = first

    # One stable channel code cannot silently change identity.
    wa_code = specs[0][1]
    identity_conflict = normalized_message(
        kind="INSTAGRAM",
        code=wa_code,
        conversation=f"identity-conflict-{suffix}",
        message=f"identity-conflict-message-{suffix}",
        text="Wrong provider identity",
    )
    identity_response = service.post("/api/v1/automation/inbox/messages", json=identity_conflict)
    assert identity_response.status_code == 409, identity_response.text
    assert detail_code(identity_response) == "CHANNEL_IDENTITY_KIND_MISMATCH", identity_response.text

    # Hot lead: Conversation -> linked ReservationRequest, never Reservation.
    wa_conversation_id = channel_results["WHATSAPP"]["conversation_id"]
    today = date.today()
    lead_payload = {
        "idempotency_key": f"block10:lead:{suffix}",
        "channel": wa_code,
        "guest_name": "Block Ten Guest",
        "phone": "+996700123456",
        "email": None,
        "check_in": (today + timedelta(days=7)).isoformat(),
        "check_out": (today + timedelta(days=9)).isoformat(),
        "adults": 2,
        "children": 0,
        "room_type_code": None,
        "notes": "Block 10 linked hot lead",
        "external_message_id": f"whatsapp-message-{suffix}-1",
        "conversation_id": wa_conversation_id,
    }
    lead = service.post("/api/v1/automation/reservation-requests", json=lead_payload)
    lead.raise_for_status()
    lead_body = lead.json()
    assert lead_body["is_reservation"] is False
    assert lead_body["status"] == "NEW"
    assert lead_body["conversation_linked"] is True
    request_id = lead_body["id"]

    replay = service.post("/api/v1/automation/reservation-requests", json=lead_payload)
    replay.raise_for_status()
    replay_body = replay.json()
    assert replay_body["idempotent_replay"] is True
    assert replay_body["id"] == request_id
    assert replay_body["conversation_linked"] is True

    changed_lead = dict(lead_payload)
    changed_lead["adults"] = 3
    lead_mismatch = service.post("/api/v1/automation/reservation-requests", json=changed_lead)
    assert lead_mismatch.status_code == 409, lead_mismatch.text
    assert detail_code(lead_mismatch) == "AUTOMATION_IDEMPOTENCY_PAYLOAD_MISMATCH", lead_mismatch.text

    linked_detail = conversation(owner, wa_conversation_id)
    assert linked_detail["conversation"]["reservation_request_id"] == request_id
    assert linked_detail["conversation"]["reservation_request_status"] == "NEW"
    assert linked_detail["conversation"]["needs_reply"] is True

    # A second automation request cannot silently steal the same conversation link.
    second_lead = dict(lead_payload)
    second_lead["idempotency_key"] = f"block10:lead-second:{suffix}"
    second_lead["external_message_id"] = f"whatsapp-message-{suffix}-2"
    second_lead["notes"] = "Must be rejected because conversation is already linked"
    already_linked = service.post("/api/v1/automation/reservation-requests", json=second_lead)
    assert already_linked.status_code == 409, already_linked.text
    assert detail_code(already_linked) == "AUTOMATION_CONVERSATION_ALREADY_LINKED", already_linked.text

    # QUEUED outbound is not delivery evidence and cannot clear needs_reply.
    queued = normalized_message(
        kind="WHATSAPP",
        code=wa_code,
        conversation=f"whatsapp-conversation-{suffix}",
        message=f"whatsapp-outbound-{suffix}-queued",
        text="Queued provider reply",
        direction="OUTBOUND",
        delivery="QUEUED",
    )
    queued_result = ingest(service, queued)
    assert queued_result["counts_as_response"] is False
    assert conversation(owner, wa_conversation_id)["conversation"]["needs_reply"] is True

    # The provider message id is immutable: a new idempotency key cannot rewrite message content.
    provider_collision = dict(queued)
    provider_collision["idempotency_key"] = f"block10:{wa_code}:provider-collision:{suffix}"
    provider_collision["text"] = "Different content behind same provider message id"
    collision = service.post("/api/v1/automation/inbox/messages", json=provider_collision)
    assert collision.status_code == 409, collision.text
    assert detail_code(collision) == "PROVIDER_MESSAGE_IDENTITY_MISMATCH", collision.text

    # A legitimate delivery receipt may upgrade the same provider message from QUEUED -> SENT.
    delivered = dict(queued)
    delivered["idempotency_key"] = f"block10:{wa_code}:delivery-receipt:{suffix}"
    delivered["delivery_status"] = "SENT"
    delivered["raw_payload"] = {"block": 10, "receipt": "provider-sent"}
    delivered_result = ingest(service, delivered)
    assert delivered_result["reconciled_existing_message"] is True
    assert delivered_result["idempotent_replay"] is False
    assert delivered_result["counts_as_response"] is True
    assert delivered_result["delivery_status"] == "SENT"
    after_delivery = conversation(owner, wa_conversation_id)
    assert after_delivery["conversation"]["needs_reply"] is False
    assert after_delivery["conversation"]["first_response_at"] is not None

    # A delivery regression for the same provider message is rejected.
    regression = dict(delivered)
    regression["idempotency_key"] = f"block10:{wa_code}:delivery-regression:{suffix}"
    regression["delivery_status"] = "QUEUED"
    delivery_regression = service.post("/api/v1/automation/inbox/messages", json=regression)
    assert delivery_regression.status_code == 409, delivery_regression.text
    assert detail_code(delivery_regression) == "PROVIDER_MESSAGE_STATUS_REGRESSION", delivery_regression.text

    # A newer inbound message makes the same conversation need a reply again.
    next_inbound = normalized_message(
        kind="WHATSAPP",
        code=wa_code,
        conversation=f"whatsapp-conversation-{suffix}",
        message=f"whatsapp-message-{suffix}-3",
        text="Guest replied again",
    )
    ingest(service, next_inbound)
    assert conversation(owner, wa_conversation_id)["conversation"]["needs_reply"] is True

    # A separate provider-confirmed SENT message also clears needs_reply.
    sent = normalized_message(
        kind="WHATSAPP",
        code=wa_code,
        conversation=f"whatsapp-conversation-{suffix}",
        message=f"whatsapp-outbound-{suffix}-sent",
        text="Second provider-confirmed reply",
        direction="OUTBOUND",
        delivery="SENT",
    )
    sent_result = ingest(service, sent)
    assert sent_result["counts_as_response"] is True
    after_sent = conversation(owner, wa_conversation_id)
    assert after_sent["conversation"]["needs_reply"] is False

    # Another guest reply restores the needs-reply fact.
    final_inbound = normalized_message(
        kind="WHATSAPP",
        code=wa_code,
        conversation=f"whatsapp-conversation-{suffix}",
        message=f"whatsapp-message-{suffix}-4",
        text="Guest asks one more question",
    )
    ingest(service, final_inbound)
    assert conversation(owner, wa_conversation_id)["conversation"]["needs_reply"] is True

    # Website remains direct Core booking contract, not an n8n/service-key path.
    website = httpx.post(
        f"{BASE}/api/v1/booking/requests",
        json={
            "guest_name": "Website Block Ten",
            "phone": "+996700777888",
            "check_in": (today + timedelta(days=10)).isoformat(),
            "check_out": (today + timedelta(days=12)).isoformat(),
            "adults": 2,
            "children": 0,
            "source": "WEB",
            "notes": "Website direct Core contract",
        },
        timeout=30.0,
    )
    website.raise_for_status()
    website_body = website.json()
    assert website_body["is_reservation"] is False
    assert website_body["status"] == "NEW"

    # Automation service credential cannot use manager payment authority.
    forbidden_payment = service.post(
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        json={
            "amount_kgs": 1000,
            "method": "AUTOMATION_FORBIDDEN",
            "external_ref": f"BLOCK10-FORBIDDEN-{suffix}",
            "idempotency_key": f"block10-forbidden-payment-{suffix}",
        },
    )
    assert forbidden_payment.status_code in {401, 403}, forbidden_payment.text

    request_truth = service.get(f"/api/v1/automation/read/reservation-requests/{request_id}")
    request_truth.raise_for_status()
    truth_body = request_truth.json()
    assert truth_body["request"]["is_reservation"] is False
    assert truth_body["reservation"] is None
    assert truth_body["payments"]["received_kgs"] == 0

    # Canonical n8n workflow is a source contract, not deployment evidence.
    workflow_path = Path("automation/n8n/unified-client-channel-core.json")
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    names = {node["name"] for node in workflow["nodes"]}
    for required in {
        "Core Ingest Inbound",
        "Core Verified Hotel Facts",
        "Core Check Availability",
        "Core Create Linked ReservationRequest",
        "Compose Verified Draft",
        "Build Safe Provider Handoff",
    }:
        assert required in names, required
    raw = workflow_path.read_text(encoding="utf-8")
    assert "/api/v1/automation/inbox/messages" in raw
    assert "/api/v1/automation/reservation-requests" in raw
    assert "conversation_id" in raw
    assert "auto_sent:false" in raw
    assert "provider_send_required:true" in raw
    assert "/confirm-payment" not in raw
    assert "nfc-charge" not in raw.lower()
    assert "postgresql://" not in raw.lower()

    readme = Path("automation/n8n/README.md").read_text(encoding="utf-8")
    assert "inbox-first" in readme
    assert "not the canonical launch workflow" in readme
    assert "Templates are source artifacts" in readme

    service.close()
    owner.close()
    print(
        "PASS: Block 10 unifies WhatsApp/Instagram/Telegram audit, payload-safe idempotency, "
        "provider-message identity/delivery reconciliation, linked ReservationRequest handoff, "
        "provider-evidenced response state and website direct-Core authority boundary"
    )


if __name__ == "__main__":
    main()
