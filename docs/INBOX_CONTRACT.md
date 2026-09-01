# THREE CROWNS — UNIFIED INBOX CONTRACT

Version: 1.1
Date: 2026-09-01
Status: IMPLEMENTED CORE CONTRACT / PROVIDER CREDENTIALS AND EXTERNAL WEBHOOKS NOT VERIFIED AS DEPLOYED

## 1. Purpose

Messaging channels converge into one canonical Resort OS model:

`CHANNEL ADAPTER -> NORMALIZED MESSAGE -> RESORT CORE -> CONVERSATION -> MESSAGE -> MANAGER CONTROL`

Provider-specific webhook formats are adapter concerns. They must not leak into the canonical PMS domain.

The public website booking form remains a deterministic direct Core path:

`WEBSITE -> /api/v1/booking/requests -> ReservationRequest`

The browser is not given an automation service credential merely to imitate a messaging channel.

## 2. Canonical entities

### CommunicationChannel

Represents one known communication account/channel for the property.

Canonical fields include:
- property;
- stable code;
- kind: `WEBSITE | TELEGRAM | WHATSAPP | INSTAGRAM | OTHER`;
- display name;
- optional external account identifier;
- active flag;
- optional metadata.

A channel code has stable identity. Reusing the same code with another kind, or with a conflicting non-null external account id, is a contract conflict rather than an upsert that silently changes channel identity.

### Conversation

Represents one guest/contact dialogue in one channel.

Canonical fields include:
- external conversation/contact identifiers;
- contact name/phone/username when known;
- status: `OPEN | WAITING_GUEST | WAITING_STAFF | RESOLVED | ARCHIVED`;
- optional manager assignee;
- optional `ReservationRequest` relation;
- last inbound/outbound timestamps;
- first response timestamp;
- resolved timestamp.

### ConversationMessage

Represents one canonical message/event inside a conversation.

Direction:
- `INBOUND` — provider-evidenced guest/customer input;
- `OUTBOUND` — provider-evidenced outbound delivery attempt/result ingested by an adapter;
- `INTERNAL` — Resort OS staff note or AI draft that is never proof of external delivery.

Delivery status:
- `RECEIVED`;
- `QUEUED`;
- `SENT`;
- `DELIVERED`;
- `FAILED`;
- `UNKNOWN`.

## 3. Normalized ingress

Protected endpoint:

`POST /api/v1/automation/inbox/messages`

Authentication:

`X-Resort-Service-Key`

For automated Instagram / WhatsApp / Telegram messaging flows this ingest is mandatory and occurs before AI qualification or ReservationRequest handoff.

A provider adapter is responsible for validating its provider webhook/request before submitting normalized facts to Resort Core.

Required conceptual input:
- idempotency key;
- channel code/kind/display name;
- external conversation identifier;
- direction;
- sender type;
- text and/or raw payload.

Optional input includes external account/contact/message ids, contact details, content type, delivery status and provider timestamp.

## 4. Idempotency

Inbound adapter delivery must be retry-safe and payload-safe.

Two layers exist:
1. `AutomationInboundEvent` keyed by property + source + idempotency key;
2. message uniqueness keyed by conversation + external message id when the provider supplies one.

Rules:
- same idempotency key + same payload = replay;
- same idempotency key + different payload = `409` conflict;
- same provider external message id in the same conversation = replay, never a second message;
- an idempotency conflict must be reconciled, not automatically retried with modified content.

The same payload-safety rule applies to automation ReservationRequest intake and controlled outbound dispatch.

## 5. Response-control rule

Current `needs_reply` is a deterministic fact, not an SLA opinion.

A conversation needs a reply when:
- it has an inbound timestamp;
- there is no provider-confirmed outbound timestamp after that inbound;
- conversation status is not `RESOLVED` or `ARCHIVED`.

Only outbound `SENT` or `DELIVERED` evidence advances the canonical last-outbound response fact.

`QUEUED`, `FAILED`, and `UNKNOWN` do not clear `needs_reply`.

NO SLA THRESHOLD IS CURRENTLY DEFINED.

Therefore Resort OS must not label a dialogue `OVERDUE`, `LATE`, or equivalent until an explicit owner rule exists.

## 6. Assignment

Only active `OWNER` or `MANAGER` users may be assigned to manager Inbox conversations in the current contract.

Manager can:
- claim an unassigned conversation;
- explicitly assign/unassign through the manager API;
- change conversation status;
- link/unlink a `ReservationRequest`;
- create an INTERNAL note;
- create an AI draft when the configured provider is available.

AI drafts remain INTERNAL and are not proof of sending.

## 7. Reservation linkage and hot-lead handoff

Conversation and ReservationRequest are distinct entities.

A dialogue may exist without a booking request.
A website booking request may exist without a messaging dialogue.

When automated messaging creates a hot lead:
1. inbox ingest creates/returns the canonical `conversation_id`;
2. automation calls `POST /api/v1/automation/reservation-requests` with that `conversation_id`;
3. Core creates only a `ReservationRequest`;
4. Core atomically links `Conversation.reservationRequestId` to that request;
5. response remains `is_reservation=false`.

A conversation already linked to a different request cannot silently be relinked by automation.

The link never turns a conversation or request into a guaranteed reservation.

## 8. External sending boundary

Resort Core does not pretend that WhatsApp or Instagram delivery happened without provider evidence.

Provider-specific n8n/ManyChat/API Green adapters own actual delivery and must write the result back through the normalized inbox endpoint.

A controlled direct Telegram adapter exists in source for Telegram manager sending. Even there, a provider timeout/transport ambiguity becomes `UNKNOWN`/reconciliation-required rather than a fabricated success.

Outbound dispatch idempotency is payload-safe: the same key cannot be reused to send different text.

## 9. Provider adapter responsibilities

Each provider adapter must handle provider-specific concerns outside canonical Core logic:
- webhook authentication/signature/token verification when supported;
- provider event parsing;
- provider pagination/retry semantics;
- provider message identifiers;
- media download/reference handling;
- outbound API authentication;
- provider rate limits;
- provider delivery receipts/errors;
- conversion into the normalized Core contract.

The adapter must not write directly to PostgreSQL.

For ManyChat/API Green/OpenAI, source templates are not deployment evidence. Credentials and external webhook acceptance are separate launch gates.

## 10. AI boundary

AI may:
- extract/qualify conversation facts;
- ask for missing dates/guest count;
- use Core availability and prices;
- draft customer-facing text;
- create a ReservationRequest through the controlled automation endpoint;
- hand the hot lead to a manager.

AI must not:
- invent availability, price, discount or policy;
- infer/negotiate prepayment amount, terms or method;
- create payment links/QR as authority;
- confirm payment;
- create a guaranteed reservation;
- invent that an external reply was delivered;
- manufacture provider delivery state;
- bypass manager/payment controls;
- write PostgreSQL.

Tool failure or unknown provider result must never be described as success.

## 11. n8n canonical workflow

`automation/n8n/unified-client-channel-core.json` is the canonical provider-neutral messaging workflow for Block 10.

It performs:

`NORMALIZE -> CORE INBOX INBOUND -> VERIFIED FACTS -> AI EXTRACTION -> CORE AVAILABILITY -> OPTIONAL LINKED ReservationRequest -> AI DRAFT -> PROVIDER HANDOFF`

It intentionally returns `auto_sent=false` and requires the provider adapter to send and report outbound evidence.

`whatsapp-green-ai-admin.json` remains an earlier provider-specific prototype and is not the canonical launch workflow until it follows the same inbox-first and evidence-return rules.

## 12. Current implementation

Implemented source contract:
- Prisma communication domain in `packages/database/prisma/schema.prisma`;
- normalized ingest in `services/api/app/communication_ingest.py`;
- automation ReservationRequest linking in `services/api/app/automation.py`;
- manager API in `services/api/app/inbox.py`;
- manager AI draft in `services/api/app/ai_sales.py`;
- controlled Telegram adapter and outbound reconciliation logic;
- manager UI in `apps/admin/components/InboxBoard.tsx`;
- Command Center communication metrics;
- canonical n8n unified-client workflow template;
- CI contract verification.

Provider credentials/external production webhooks remain launch infrastructure and are not declared connected by this contract.
