# Three Crowns n8n automation boundary

Status: **ACTIVE V1 CLIENT-AUTOMATION ARCHITECTURE / TEMPLATES NOT DEPLOYED**.

Owner decision for V1 client work:

- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram / other channels may also be orchestrated by n8n where useful;
- public website -> Resort Core directly for deterministic availability, pricing and ReservationRequest creation.

n8n owns conversation orchestration. Resort Core owns hotel truth.

The V1 sales objective is **qualification and hot-lead handoff to a manager**, not automated payment collection.

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

- choose or negotiate the manager's prepayment amount/terms;
- generate a payment link/QR as part of the V1 sales flow;
- collect or confirm prepayment;
- choose a payment method for the guest;
- create a guaranteed reservation;
- check a guest in;
- check a guest out;
- issue refunds;
- mutate hotel money;
- write PostgreSQL;
- invent hotel policies or prices.

Prepayment is handled manually by the hotel manager. Resort OS may later contain the manager-confirmed payment/reservation fact for internal PMS/finance visibility, but n8n does not make that decision.

## Client sales flow

Recommended orchestration:

1. Channel message arrives in ManyChat/API Green/other connector.
2. n8n extracts the minimum structured facts from the conversation.
3. If dates/guest count are incomplete, n8n asks the client for them.
4. n8n calls `check-availability`.
5. n8n presents only returned sellable categories/prices.
6. n8n answers hotel questions from approved Core guest facts only.
7. When the guest shows intent to continue, n8n collects contact details and creates a `ReservationRequest` using a stable idempotency key.
8. n8n treats this as a **hot qualified lead** and hands the guest/request to a manager.
9. The manager independently decides and collects prepayment.
10. Future status questions may use `/automation/read/reservation-requests/{request_id}`.
11. Only when Core contains an actual Reservation may the workflow tell the guest that a booking/reservation exists.

The handoff target is therefore:

`DATES + GUESTS + CONTACT + SELECTED/INTERESTED CATEGORY + CURRENT CORE PRICE + RESERVATION_REQUEST_ID -> MANAGER`

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
3. Automation stops at qualification/handoff; the manager handles prepayment manually.
4. Without a manager-confirmed reservation fact, automation must not say that the room is booked.
5. The old public-site statement about keeping an unpaid preliminary booking for two days is stale and must not drive automation.
6. Availability and prices come only from Resort Core.
7. Payment received may be stated only when Core exposes a manager-confirmed `RECEIVED` payment fact.
8. n8n must not infer the required prepayment amount or payment method from static configuration.
9. Channel delivery success belongs to n8n/provider evidence, not to Resort Core assumptions.
10. Unknown policy remains unknown; hand off to a manager instead of inventing an answer.

## Existing templates

- `guest-sales-context.json` — approved hotel facts + deterministic availability/pricing context for the AI conversation.
- `reservation-intake-core.json` — normalized hot lead -> availability -> ReservationRequest.
- `staff-intake-core.json` — normalized staff input -> operational task.

Provider-specific ManyChat/API Green workflows are intentionally outside Resort Core and should be assembled in n8n when credentials are connected.
