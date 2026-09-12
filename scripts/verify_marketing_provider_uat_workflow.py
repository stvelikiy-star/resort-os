#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "automation" / "n8n" / "marketing-whatsapp-green-provider-uat.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")
    workflow = json.loads(raw)
    nodes = workflow.get("nodes") or []
    names = {node.get("name"): node for node in nodes}

    require(workflow.get("active") is False, "provider UAT workflow must remain inactive")
    require("Manual UAT Trigger" in names, "workflow must be manual-triggered")
    require(not any(node.get("type") == "n8n-nodes-base.scheduleTrigger" for node in nodes), "scheduled sending is forbidden during UAT")
    require(not any(node.get("type") == "n8n-nodes-base.webhook" for node in nodes), "provider UAT sender must not expose a webhook trigger")

    forbidden_db = {
        "n8n-nodes-base.postgres",
        "n8n-nodes-base.mysql",
        "n8n-nodes-base.microsoftSql",
    }
    require(not any(node.get("type") in forbidden_db for node in nodes), "workflow must not access databases directly")

    audience = names.get("Load Consent Gated Audience")
    require(audience is not None, "consent-gated audience read is required")
    audience_text = json.dumps(audience, ensure_ascii=False)
    require("/api/v1/integrations/marketing/audience" in audience_text, "audience must come from Resort Core")
    require("X-Resort-Service-Key" in audience_text and "AUTOMATION_SERVICE_KEY" in audience_text, "audience read must use service auth")
    require("channel=WHATSAPP" in audience_text, "UAT sender must use WHATSAPP audience")

    candidate = names.get("Build Exact UAT Candidate")
    require(candidate is not None, "exact UAT candidate gate is required")
    candidate_text = json.dumps(candidate, ensure_ascii=False)
    for token in (
        "MARKETING_PROVIDER_UAT_SEND_ENABLED",
        "MARKETING_PROVIDER_UAT_REQUEST_ID",
        "MARKETING_PROVIDER_UAT_MESSAGE",
        "payload.consent_required",
        "payload.service_authenticated",
        "candidate",
        "canSend",
    ):
        require(token in candidate_text, f"missing fail-closed UAT token: {token}")
    require("===\"true\"" in candidate_text or "==='true'" in candidate_text, "send enable must require an explicit true value")

    gate = names.get("Exact UAT Send Allowed?")
    require(gate is not None, "explicit IF send gate is required")
    require("can_send" in json.dumps(gate, ensure_ascii=False), "send gate must depend on can_send")

    green = names.get("GREEN Send One UAT Message")
    require(green is not None, "GREEN API send node is required for supervised UAT")
    green_text = json.dumps(green, ensure_ascii=False)
    require("GREEN_API_ID_INSTANCE" in green_text and "GREEN_API_TOKEN_INSTANCE" in green_text, "GREEN provider credentials must come from environment")
    require("/sendMessage/" in green_text, "GREEN API sendMessage endpoint is required")
    require("chatId" in green_text and "message" in green_text, "GREEN request must contain chatId and message")

    record = names.get("Record SENT In Resort Core")
    require(record is not None, "successful provider send must be recorded in Resort Core")
    record_text = json.dumps(record, ensure_ascii=False)
    require("/api/v1/integrations/marketing/provider-events" in record_text, "provider event endpoint is required")
    require("event_type" in record_text and "SENT" in record_text, "successful UAT must record SENT")
    require("provider_message_id" in record_text, "provider message id must be preserved")
    require("X-Resort-Service-Key" in record_text and "AUTOMATION_SERVICE_KEY" in record_text, "provider event must use service auth")

    blocked = names.get("Blocked Safe Result")
    require(blocked is not None, "disabled gate must terminate safely without sending")
    require("NO_MESSAGE_SENT" in json.dumps(blocked, ensure_ascii=False), "blocked branch must explicitly report no send")

    connections = workflow.get("connections") or {}
    gate_routes = ((connections.get("Exact UAT Send Allowed?") or {}).get("main") or [])
    require(len(gate_routes) == 2, "send gate must have true and false branches")
    true_nodes = {entry.get("node") for entry in (gate_routes[0] or [])}
    false_nodes = {entry.get("node") for entry in (gate_routes[1] or [])}
    require("GREEN Send One UAT Message" in true_nodes, "only true gate may reach provider send")
    require("Blocked Safe Result" in false_nodes, "false gate must end in safe blocked result")

    print("PASS: provider UAT workflow is inactive and manual-only")
    print("PASS: consent-gated audience and service auth are mandatory")
    print("PASS: exact request id + explicit enable + explicit message gate provider send")
    print("PASS: no schedule/webhook/direct database access exists")
    print("PASS: successful GREEN send requires provider id and records SENT in Resort Core")
    print("PASS: disabled path explicitly sends no message")


if __name__ == "__main__":
    main()
