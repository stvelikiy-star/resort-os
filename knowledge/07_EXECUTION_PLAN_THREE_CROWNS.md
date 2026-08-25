# THREE CROWNS — ACTIVE EXECUTION PLAN

Version: 1.1
Date: 2026-08-25
Status: ACTIVE
Scope: Current implementation order for «Три Короны»

Critical rule: implement only evidence-backed requirements. Unknown business rules remain UNKNOWN / DECISION REQUIRED.

## 1. Explicit freeze

NFC / wristband / internal-wallet work is DEFERRED and excluded from the active engineering queue until the owner explicitly reactivates it.

Existing NFC code is retained as dormant implementation evidence. No further NFC feature development, provider integration, UX expansion or production activation is part of the current plan.

## 2. Client automation boundary — owner decision

Customer-channel work is orchestrated through **n8n**, not through provider-specific business logic inside Resort Core.

Current owner-selected channel path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram / other client channels may also be orchestrated through n8n where appropriate;
- website booking talks to Resort Core directly for deterministic availability/pricing/request creation.

Resort Core remains the source of operational truth and exposes controlled APIs/tools to n8n. n8n may orchestrate conversations, AI extraction/replies and channel delivery, but it must not bypass Core and write PostgreSQL directly.

Core responsibilities for client automation:
- deterministic availability and pricing facts;
- create/read ReservationRequest;
- expose reservation/payment status facts;
- expose approved hotel facts required for replies;
- optional normalized communication/audit ingestion;
- idempotency and service authentication;
- deny AI/n8n direct authority to confirm payment, create a guaranteed reservation, check-in/check-out, refund or mutate hotel money outside approved deterministic flows.

Direct provider adapters already present in the repository may be retained as optional/reference code, but they are not an active dependency for V1 and must not distract from hotel operations, automation contracts or the public site.

## 3. Active engineering order

P0/P1 order:

1. PMS daily management surface for owner/reception.
2. Reservation and stay visibility using existing confirmed lifecycle.
3. Housekeeping and maintenance operational control.
4. Owner Command Center and cross-module analytics.
5. Stable n8n/Core automation contracts for client work.
6. AI Sales/Concierge through n8n over controlled Core tools only.
7. Whisper/audio staff intake and staff automation.
8. Real hotel payment-provider adapter and webhook verification after provider selection/credentials.
9. Public-site production completion with owned media and final room content.
10. Production hardening, migrations, backup/restore, monitoring, staging, rollback and cutover.
11. Dining management after exact operational rules are confirmed.
12. Store management after ownership/accounting boundary is confirmed.
13. QR service points / access / billiards after exact operating rules/equipment are known.
14. LED content management after hardware/protocol inventory is known.

## 4. Work that may proceed without further owner input

- dashboards and read-only analytics derived from existing canonical entities;
- richer search/filtering over existing PMS data;
- reservation/guest/payment/audit detail views where data already exists;
- housekeeping/maintenance assignment and status visibility using existing confirmed states;
- provider-neutral Inbox/Conversation/Message foundation when useful for audit/control, without making it a dependency on direct provider integration;
- guarded n8n/service contracts;
- deployment manifests, environment templates, health/readiness, logging, migrations, backup/restore and test scaffolding;
- public-site integration with existing Core availability/request endpoints;
- staff automation using existing confirmed task/status rules.

## 5. Work that must NOT be invented

Do not invent:

- cancellation/refund/no-show penalties;
- walk-in/group/waitlist rules;
- early-arrival/late-departure charges;
- exact dining entitlements/checklists beyond confirmed tariff facts;
- store ownership/accounting if not confirmed;
- entrance hardware/protocol;
- QR-toilet exact workflow if not confirmed;
- billiards pricing/booking rules;
- LED controller/device protocol;
- payment provider/webhook behavior before a provider is selected;
- production ManyChat/API Green credentials or provider-specific assumptions not supplied by the owner/integration;
- any production data or financial values not read from authoritative data.

## 6. Verification rule

Every change is classified as IMPLEMENTED until explicit test/build/runtime evidence exists. GitHub Actions infrastructure failures before any workflow step starts are not classified as code failures.

Development order:

KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE
