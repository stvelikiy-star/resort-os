# THREE CROWNS — CLIENT AUTOMATION / n8n BOUNDARY

Date: 2026-08-25
Status: OWNER-CONFIRMED / ACTIVE
Canonical decision: YES

## Decision

Client communication/orchestration is handled through **n8n**.

Confirmed channel path from the owner:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- other client channels may also be orchestrated by n8n;
- the public booking website talks to Resort Core directly for deterministic hotel operations.

## Resort OS responsibility

Resort OS is not required to become a provider-specific CRM or channel gateway.

Its active responsibilities are:
- public website;
- PMS / reception;
- room inventory and availability;
- rates and deterministic pricing;
- ReservationRequest / Reservation / Stay lifecycle;
- hotel payments through a controlled provider adapter when selected;
- housekeeping;
- maintenance;
- staff interfaces and automation;
- owner/manager Command Center;
- audit, RBAC, realtime and operational reporting;
- controlled API/tool surface for n8n.

## n8n responsibility

n8n handles customer-facing orchestration, including where configured:
- receiving messages from ManyChat / API Green / Telegram / other channels;
- AI extraction and dialogue orchestration;
- calling Resort Core for authoritative availability, price, request and reservation facts;
- creating ReservationRequest through allowed Core API;
- sending replies through connected channel providers;
- logging normalized communication events to Core when useful for audit/control.

## Security / truth boundary

n8n and AI must not:
- write directly to PostgreSQL;
- invent availability or price;
- treat ReservationRequest as Reservation;
- confirm a payment without a Core/provider fact;
- create guaranteed reservations outside the controlled conversion flow;
- check guests in/out without approved hotel actions;
- mutate hotel money outside approved deterministic payment routes.

## Existing direct channel code

Any direct Telegram Sales/provider adapter code already present in the repository is optional/reference implementation only. It is not an active dependency for V1 and should not consume engineering priority unless the owner explicitly requests it.

## Active focus after this decision

1. PMS / reception / reservations / stays.
2. Housekeeping and maintenance automation.
3. Staff PWA / Telegram staff workflows.
4. Command Center and reporting.
5. Stable n8n/Core automation contracts.
6. Public website and booking UX.
7. Production migrations, backup/restore, monitoring and deployment.
8. Real payment-provider integration after provider selection.
9. Remaining dining/store/access/QR/billiards/LED modules only after exact rules are confirmed.
10. NFC remains deferred.
