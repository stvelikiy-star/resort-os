# Three Crowns n8n automation boundary

Status: **IMPLEMENTED AS IMPORTABLE TEMPLATES / NOT DEPLOYED**.

n8n is an orchestration layer. It must not connect directly to PostgreSQL and must not implement booking, pricing, payment, NFC, stay or room-state rules itself.

## Allowed Core calls

The service-authenticated Core contract is the authority:

- `GET /api/v1/booking/check-availability`
- `POST /api/v1/automation/reservation-requests`
- `POST /api/v1/automation/staff-intake`

Header for protected automation routes:

`X-Resort-Service-Key: <AUTOMATION_SERVICE_KEY>`

AI/n8n must not call payment confirmation, guaranteed-reservation creation, check-in, check-out, refund or NFC charge routes.

## Runtime variables

Configure these in the n8n runtime, never in workflow JSON:

- `RESORT_CORE_URL` — e.g. `https://api.3korony.com`
- `AUTOMATION_SERVICE_KEY` — same secret configured in Resort Core

Provider/channel credentials (Telegram, Meta/WhatsApp/Instagram, OpenAI) are intentionally not committed here.

## Templates

- `reservation-intake-core.json` — normalized reservation lead → availability → `ReservationRequest`.
- `staff-intake-core.json` — normalized staff/voice result → operational task.

These templates accept **structured normalized input**. Channel-specific parsing, speech-to-text and LLM extraction are separate adapters and must produce the contracts documented below.

## Reservation adapter input

```json
{
  "channel": "TELEGRAM",
  "message_id": "provider-message-id",
  "guest_name": "Guest name",
  "phone": "+996...",
  "email": null,
  "check_in": "2026-08-27",
  "check_out": "2026-08-29",
  "adults": 2,
  "children": 0,
  "room_type_code": null,
  "notes": "Original guest request"
}
```

The workflow derives the idempotency key from `channel + message_id`, checks availability, and creates only a `ReservationRequest`. It never claims a guaranteed reservation exists.

## Staff adapter input

```json
{
  "channel": "TELEGRAM",
  "message_id": "provider-message-id",
  "sender_id": "provider-user-id",
  "intent": "MAINTENANCE",
  "room_code": "101",
  "transcript": "В 101 номере течёт кран",
  "summary": "Течёт кран",
  "priority": "HIGH"
}
```

Allowed intents: `MAINTENANCE`, `HOUSEKEEPING`, `GUEST_REQUEST`.

## Truth rules

1. Tool failure/timeout/unknown result must never be described as success.
2. Availability is informational until the controlled reservation/payment flow creates a guaranteed reservation.
3. A successful automation reservation intake returns `is_reservation=false`.
4. Every provider event needs a stable provider message/event ID. Do not generate a new idempotency key on retry.
5. Channel adapters must preserve the original provider message ID and original text/transcript for auditability.
