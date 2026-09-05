# Three Crowns n8n automation boundary

Status: **ACTIVE V1 CLIENT-AUTOMATION ARCHITECTURE / TEMPLATES NOT DEPLOYED**.

Owner decision for V1 client work:

- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram may use n8n or the controlled direct Telegram adapter;
- public website booking -> Resort Core directly.

n8n owns provider conversation orchestration. Resort Core owns hotel truth and the controlled communication audit.

The V1 sales objective is **qualification and hot-lead handoff to a manager**, not automated payment collection.

n8n must **not** connect directly to PostgreSQL and must not reimplement booking, pricing, payment, stay or room-state rules.

## Authentication

Protected automation routes require:

`X-Resort-Service-Key: <AUTOMATION_SERVICE_KEY>`

Runtime variables belong in n8n credentials/environment, never committed to workflow JSON:

- `RESORT_CORE_URL`
- `AUTOMATION_SERVICE_KEY`
- ManyChat/API Green/channel credentials
- `OPENAI_API_KEY`
- `OPENAI_SALES_MODEL`

## Canonical messaging-channel sequence

For Instagram / WhatsApp / Telegram messaging automation the sequence is mandatory:

1. provider event is normalized by n8n/provider adapter;
2. n8n writes the inbound event to `POST /api/v1/automation/inbox/messages`;
3. Core returns the canonical `conversation_id`;
4. n8n reads approved hotel facts and deterministic availability only from Core;
5. AI may extract/qualify facts and draft a reply;
6. if the guest becomes a hot lead, n8n creates only a `ReservationRequest` and supplies that `conversation_id`;
7. Core atomically links `Conversation.reservationRequestId` to the created request;
8. provider adapter sends the reply outside Core;
9. provider-confirmed outbound evidence is written back through `/api/v1/automation/inbox/messages`;
10. only outbound `SENT`/`DELIVERED` evidence clears the inbox `needs_reply` state.

A provider delivery timeout/UNKNOWN must never be described as success and must not be blindly retried when the provider has no client idempotency guarantee.

## Website boundary

The public website remains intentionally different from messaging channels:

`Website -> Resort Core /api/v1/booking/requests`

The authoritative website artifact is the Core `ReservationRequest`; the browser does not receive an automation service key and does not write directly to communication tables. The website must not be routed through n8n just to mimic a chat channel.

## Stable Core calls for client automation

### Unified communication audit — required for messaging channels

- `POST /api/v1/automation/inbox/messages`

The same idempotency key with the same payload is a replay. The same key with a different payload is a conflict and must be investigated rather than retried.

A `channel_code` has stable identity. Reusing the same code with a different channel kind/account is a conflict.

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

When the lead came from unified inbox, send `conversation_id`. Core must return `conversation_linked=true`.

### Staff automation

- `POST /api/v1/automation/staff-intake`

Use only for already-structured staff operations that follow confirmed Core task/status rules.

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

Prepayment is handled manually by the hotel manager. Resort OS may contain manager-confirmed payment/reservation facts for internal PMS/finance visibility, but n8n does not make that decision.

## Canonical sales workflow template

`unified-client-channel-core.json` is the canonical provider-neutral workflow for Instagram / WhatsApp / Telegram messaging automation.

It:

- requires a normalized provider message;
- persists inbound to the Core unified inbox first;
- reads verified guest facts;
- uses AI only to extract facts/draft text;
- calls deterministic Core availability;
- creates a linked `ReservationRequest` only for a qualified booking intent;
- returns a draft/provider handoff with `auto_sent=false`;
- requires provider delivery evidence to be written back to Core.

Provider-specific ManyChat/API Green adapters should normalize into this workflow. Provider credentials are not committed to Git and are not considered deployed merely because a template exists.

`whatsapp-green-ai-admin.json` is retained as a provider/reference prototype from the earlier phase. It is **not the canonical launch workflow** because Block 10 requires the unified inbox-first contract. Do not activate it instead of `unified-client-channel-core.json` without updating it to the same audit/handoff rules.

## Standalone reservation adapter input

`reservation-intake-core.json` remains a smaller controlled adapter when facts are already structured. When `conversation_id` is supplied it must link the request back to that inbox conversation.

```json
{
  "channel": "WHATSAPP_GREEN",
  "message_id": "provider-message-id",
  "conversation_id": "uuid-from-core-inbox",
  "guest_name": "Guest name",
  "phone": "+996...",
  "email": null,
  "check_in": "2026-09-05",
  "check_out": "2026-09-07",
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

Do not infer urgency rules unless explicitly approved. `NORMAL` is the safe default for automated staff intake.

## Truth rules

1. Tool failure, timeout or unknown result must never be described as success.
2. `ReservationRequest != Reservation`.
3. Automation stops at qualification/handoff; the manager handles prepayment manually.
4. Without a manager-confirmed reservation fact, automation must not say that the room is booked.
5. Availability and prices come only from Resort Core.
6. Payment received may be stated only when Core exposes a manager-confirmed `RECEIVED` payment fact.
7. n8n must not infer the required prepayment amount or payment method from static configuration.
8. Every messaging-channel inbound event is persisted before AI/handoff.
9. A hot lead from an inbox conversation is linked to that exact conversation.
10. Provider delivery success belongs to provider evidence, not Core assumptions.
11. Reusing an idempotency key with a different payload is a conflict.
12. Unknown policy remains unknown; hand off to a manager instead of inventing an answer.

## Existing templates

- `unified-client-channel-core.json` — canonical Instagram / WhatsApp / Telegram messaging orchestration contract.
- `guest-sales-context-core.json` — approved hotel facts + deterministic availability/pricing context.
- `reservation-intake-core.json` — structured hot lead -> availability -> linked ReservationRequest.
- `staff-intake-core.json` — normalized staff input -> operational task.
- `whatsapp-green-ai-admin.json` — earlier provider-specific reference prototype; not canonical for launch.

Templates are source artifacts, not proof that ManyChat/API Green/OpenAI credentials or external webhooks are deployed.
