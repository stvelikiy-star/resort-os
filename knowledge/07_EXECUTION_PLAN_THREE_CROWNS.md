# THREE CROWNS — ACTIVE EXECUTION PLAN

Version: 1.0
Date: 2026-08-25
Status: ACTIVE
Scope: Current implementation order for «Три Короны»

Critical rule: implement only evidence-backed requirements. Unknown business rules remain UNKNOWN / DECISION REQUIRED.

## 1. Explicit freeze

NFC / wristband / internal-wallet work is DEFERRED and excluded from the active engineering queue until the owner explicitly reactivates it.

Existing NFC code is retained as dormant implementation evidence. No further NFC feature development, provider integration, UX expansion or production activation is part of the current plan.

## 2. Active engineering order

P0/P1 order:

1. PMS daily management surface for owner/reception.
2. Reservation and stay visibility using existing confirmed lifecycle.
3. Housekeeping and maintenance operational control.
4. Unified communication inbox core model and response-control state.
5. Channel adapters: Telegram sales, WhatsApp, Instagram, website requests.
6. AI Sales & Concierge over controlled Core tools only.
7. Whisper/audio staff intake adapter.
8. Real hotel payment-provider adapter and webhook verification after provider selection/credentials.
9. Public-site production completion with owned media and final room content.
10. Dining management after exact operational rules are confirmed.
11. Store management after ownership/accounting boundary is confirmed.
12. QR service points / access / billiards after exact operating rules/equipment are known.
13. LED content management after hardware/protocol inventory is known.
14. Owner Command Center and cross-module analytics.
15. Production hardening, backup/restore, monitoring, staging, rollback and cutover.

## 3. Work that may proceed without further owner input

- dashboards and read-only analytics derived from existing canonical entities;
- richer search/filtering over existing PMS data;
- reservation/guest/payment/audit detail views where data already exists;
- housekeeping/maintenance assignment and status visibility using existing confirmed states;
- generic Inbox/Conversation/Message domain foundation without assuming provider-specific behavior;
- guarded automation/service contracts;
- deployment manifests, environment templates, health/readiness, logging and test scaffolding;
- public-site integration with existing Core availability/request endpoints.

## 4. Work that must NOT be invented

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
- Instagram handle or channel credentials;
- payment provider/webhook behavior before a provider is selected;
- any production data or financial values not read from authoritative data.

## 5. Verification rule

Every change is classified as IMPLEMENTED until explicit test/build/runtime evidence exists. GitHub Actions infrastructure failures before any workflow step starts are not classified as code failures.

Development order:

KNOWLEDGE → CURRENT STATE → GAP → PRIORITY → IMPLEMENT → TEST → EVIDENCE → VERIFIED / NOT VERIFIED → CURRENT STATE UPDATE
