# MARINA SMART — explicit guest → reception handoff contract (P0, 2026-11-06)

**One hotel's existing APIs only.** No hotel selector, no new handoff route, no
changes to the frozen public site or mobile application, no automatic provider
send, and no mutation of PMS or guest records by MARINA AI chat.

## 1. Guest asks MARINA AI a question

Canonical route `POST /api/v1/guest-os/rooms/{qr_token}/assistant/chat`.
Requires the active stay's authenticated QR/PIN guest session. Read-only response
still returns `answer`, `read_only=true` and `can_mutate=false`.

It now additionally supplies:

```json
{
  "human_handoff": {
    "available": true,
    "status": "NOT_REQUESTED",
    "request_code": "ADMIN",
    "requires_explicit_guest_action": true,
    "action": "CREATE_GUEST_REQUEST",
    "endpoint_suffix": "/requests",
    "http_method": "POST",
    "body": { "request_code": "ADMIN" },
    "task_created": false
  }
}
```

This is **only a suggested action**. It does not claim that a human is already
contacted. Do **not** auto-send this request on reading the AI answer. The
client must show a separate explicit confirmation button to the guest. The
existing public `apps/web` is frozen, so its interactive button is NOT
implemented in this PR; this response prepares an unambiguous contract for
future authorized mobile/Web integration.

## 2. Guest explicitly requests a person

Canonical route `POST /api/v1/guest-os/rooms/{qr_token}/requests` with
`{ "request_code": "ADMIN" }` and existing guest session cookie.
Optionally include the guest's written question as `description`, subject to
existing size limits. This existing route checks hotel/stay/guest QR binding,
rejects duplicate active requests, records a single `OperationalTask` with
`serviceCode=ADMIN`, adds history and audit entries. No payment is initiated.

## 3. Staff responds in existing queue

Canonical `GET /api/v1/ops/guest-requests?status=ACTIVE`, then
`POST /api/v1/ops/guest-requests/{task_id}/claim` and
`POST /api/v1/ops/guest-requests/{task_id}/complete`.

`RECEPTION`, `MANAGER`, `OWNER` can handle `ADMIN`; housekeeping and
technical staff cannot. Each route enforces property and assignment boundaries.
Guest can view task status in their own QR/PIN session.

This is **Guest OS assistance**, distinct from WhatsApp Inbox handoff.
WhatsApp phone delivery and AI-triggered automatic staff assignment remain
separate, unaccepted P0 integrations.

## Verification and limits

- Mocked FastAPI guest assistant/role tests: 11/11 PASS, including invalid
  guest session refusal, absence of guest data in AI context and proper
  `human_handoff` metadata. In a valid guest chat case no request is created.
- This patch does not claim a full live Guest OS → Staff Web browser cycle;
  the canonical Guest OS lifecycle has existing tests but a new customer still
  needs its own real-room and staff acceptance.
- No real Green API/OpenAI provider calls or messages were made.
- No owner production approval, production DNS, offsite backup or real Android
  E2E has been completed. **Commercial GO remains blocked.**
