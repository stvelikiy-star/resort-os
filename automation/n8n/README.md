# Three Crowns n8n automation boundary

Status: **ACTIVE V1 CLIENT-AUTOMATION ARCHITECTURE / TEMPLATES NOT DEPLOYED**.

Owner decision for V1 client work:

- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram / other channels may also be orchestrated by n8n where useful;
- public website -> Resort Core directly for deterministic availability, pricing and ReservationRequest creation.

n8n owns conversation orchestration. Resort Core owns hotel truth.

n8n must **not** connect directly to PostgreSQL and must not reimplement booking, pricing, payment, stay or room-state rules.

## Authentication

Protected automation routes require:

`X-Resort-Service-Key: <AUTOMATION_SERVICE_KEY>`

Runtime variables belong in n8n credentials/environment, never committed to workflow JSON:

- `RESORT_CORE_URL`
- `AUTOMATION_SERVICE_KEY`
- ManyChat/API Green/channel credentials
- OpenAI credentials used by the n8n AI workflow

## Stable Core calls for client automation

### Read-only truth

- `GET /api/v1/automation/read/hotel-facts`
- `GET /api/v1/automation/read/reservation-requests/{request_id}`
- `GET /api/v1/automation/read/reservations/{booking_number}`

### Availability and pricing

- `GET /api/v1/booking/check-availability`

Date-specific availability and price must always come from this deterministic Core route. Do not infer a live price from static room-category text.

### Create a lead/request

- `POST /api/v1/automation/reservation-requests`

This creates only a `ReservationRequest`. A successful response still has `is_reservation=false`.

### Staff automation

- `POST /api/v1/automation/staff-intake`

Use only for already-structured staff operations that follow the confirmed Core task/status rules.

### Optional audit/communication ingest

- `POST /api/v1/automation/inbox/messages`

This is optional for centralized audit/control. n8n remains responsible for actual channel delivery through ManyChat/API Green/etc.

## Forbidden authority

AI/n8n must not directly:

- confirm payment;
- create a guaranteed reservation;
- check a guest in;
- check a guest out;
- issue refunds;
- mutate hotel money;
- write PostgreSQL;
- invent hotel policies or prices.

Those actions remain controlled hotel workflows inside Resort Core/PMS.

## Reservation client flow

Recommended orchestration:

1. Channel message arrives in ManyChat/API Green/other connector.
2. n8n extracts the minimum structured facts from the conversation.
3. If dates/guest count are incomplete, n8n asks the client for them.
4. n8n calls `check-availability`.
5. n8n presents only returned sellable categories/prices.
6. When the guest wants to continue, n8n calls `POST /automation/reservation-requests` with a stable idempotency key.
7. n8n stores the returned `request_id` in the conversation workflow state.
8. Future status questions use `/automation/read/reservation-requests/{request_id}`.
9. Only when Core reports an actual Reservation may the workflow call it a booking/reservation.

## Reservation adapter input

```json
{
  "channel": "WHATSAPP",
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

Derive the idempotency key from a stable provider/channel event identifier. Never generate a new key on retry of the same event.

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
  "priority": "NORMAL"
}
```

Allowed intents: `MAINTENANCE`, `HOUSEKEEPING`, `GUEST_REQUEST`.

Do not infer urgency rules unless they are explicitly approved. `NORMAL` is the safe default for automated staff intake.

## Truth rules

1. Tool failure, timeout or unknown result must never be described as success.
2. `ReservationRequest != Reservation`.
3. Without confirmed prepayment there is no valid reservation under the current owner rule.
4. The old public-site statement about keeping an unpaid preliminary booking for two days is stale and must not drive automation.
5. Availability and prices come only from Resort Core.
6. Payment received may be stated only when Core exposes a `RECEIVED` payment fact.
7. Channel delivery success belongs to n8n/provider evidence, not to Resort Core assumptions.
8. Unknown policy remains unknown; ask a manager instead of inventing an answer.

## Existing templates

- `reservation-intake-core.json` — normalized reservation lead -> availability -> ReservationRequest.
- `staff-intake-core.json` — normalized staff input -> operational task.

Provider-specific ManyChat/API Green workflows are intentionally outside Resort Core and should be assembled in n8n when credentials are connected.
