# THREE CROWNS — UNIFIED INBOX CONTRACT

Version: 1.0
Date: 2026-08-25
Status: IMPLEMENTED CONTRACT / PROVIDER ADAPTERS NOT YET CONNECTED

## 1. Purpose

All guest communication channels must converge into one canonical Resort OS model:

`CHANNEL ADAPTER -> NORMALIZED MESSAGE -> RESORT CORE -> CONVERSATION -> MESSAGE -> MANAGER CONTROL`

Provider-specific webhook formats are adapter concerns. They must not leak into the canonical PMS domain.

## 2. Canonical entities

### CommunicationChannel

Represents one connected or known communication account/channel for the property.

Canonical fields include:
- property;
- code;
- kind: `WEBSITE | TELEGRAM | WHATSAPP | INSTAGRAM | OTHER`;
- display name;
- optional external account identifier;
- active flag;
- optional metadata.

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
- `INTERNAL` — Resort OS staff note that is never sent to the guest.

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

This endpoint accepts already-normalized facts only. A provider adapter is responsible for validating the provider webhook/request before submitting facts to Resort Core.

Required conceptual input:
- idempotency key;
- channel code/kind/display name;
- external conversation identifier;
- direction;
- sender type;
- text and/or raw payload.

Optional input includes external account/contact/message ids, contact details, content type, delivery status and provider timestamp.

## 4. Idempotency

Inbound adapter delivery must be retry-safe.

Two layers exist:
1. `AutomationInboundEvent` keyed by property + source + idempotency key;
2. message uniqueness keyed by conversation + external message id when provider supplies one.

An adapter retry must not create duplicate canonical messages.

## 5. Response-control rule

Current `needs_reply` is a deterministic fact, not an SLA opinion.

A conversation needs a reply when:
- it has an inbound timestamp;
- there is no outbound timestamp after that inbound;
- conversation status is not `RESOLVED` or `ARCHIVED`.

Current system also exposes elapsed waiting seconds.

NO SLA THRESHOLD IS CURRENTLY DEFINED.

Therefore Resort OS must not label a dialogue `OVERDUE`, `LATE`, or equivalent until an explicit owner rule exists.

## 6. Assignment

Only active `OWNER` or `MANAGER` users may be assigned to manager Inbox conversations in the current contract.

Manager can:
- claim an unassigned conversation;
- explicitly assign/unassign through the manager API;
- change conversation status;
- link/unlink a `ReservationRequest`;
- create an INTERNAL note.

## 7. Reservation linkage

Conversation and reservation request are distinct entities.

A dialogue may exist without a booking request.
A booking request may exist without a dialogue.
When evidence supports the relationship, the manager/system can link a conversation to one `ReservationRequest`.

The link never turns a conversation into a reservation.

## 8. External sending boundary

As of this contract version, Resort Core DOES NOT provide a generic endpoint that pretends to send a message to Telegram, WhatsApp or Instagram.

Outbound communication is considered externally sent only when a real provider adapter has performed the provider call and ingested the provider-evidenced result back into Resort Core.

The PMS UI therefore must not show a functioning `Send to guest` action before a real adapter exists.

## 9. Provider adapter responsibilities

Each future adapter must handle its provider-specific concerns outside canonical Core logic:
- webhook authentication/signature verification when supported;
- provider event parsing;
- provider pagination/retry semantics;
- provider message identifiers;
- media download/reference handling;
- outbound API authentication;
- provider rate limits;
- provider delivery receipts/errors;
- conversion into the normalized Core contract.

The adapter must not write directly to PostgreSQL.

## 10. AI boundary

AI may operate through controlled Core and adapter tools only.

AI must not:
- invent that an external reply was delivered;
- manufacture provider delivery state;
- create a guaranteed reservation from conversation context alone;
- confirm payment;
- bypass manager/payment controls.

Tool failure or unknown provider result must never be described as success.

## 11. Current implementation

Implemented code:
- Prisma communication domain in `packages/database/prisma/schema.prisma`;
- normalized ingest in `services/api/app/communication_ingest.py`;
- manager API in `services/api/app/inbox.py`;
- manager UI in `apps/admin/components/InboxBoard.tsx`;
- Command Center communication metrics;
- `.github/workflows/inbox-ci.yml` verification workflow.

Provider adapters are NOT yet connected.

## 12. Next provider sequence

Only after credentials/provider contracts are available:
1. Telegram sales adapter;
2. WhatsApp adapter;
3. Instagram adapter;
4. outbound delivery + receipts;
5. AI extraction/reply orchestration over the same normalized model.

Exact provider order may change only with an explicit project decision.
