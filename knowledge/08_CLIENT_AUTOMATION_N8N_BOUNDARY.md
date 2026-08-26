# THREE CROWNS — CLIENT AUTOMATION / n8n BOUNDARY

Version: 1.1
Date: 2026-08-26
Status: SUPPORTING OWNER-DECISION EXTRACT / ACTIVE
Canonical: NO
Decision authority: `05_DECISIONS_AND_BACKLOG.md` — D-019, D-020, D-021
Current-state authority: `04_CURRENT_STATE.md`

This file is a practical implementation/reference extract for Three Crowns. It does not create independent canonical Product, Domain, AI, payment or Current State truth.

---

## 1. Approved client-channel decision

Client communication/orchestration is handled through **n8n** over controlled Resort Core interfaces.

Approved Three Crowns path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- other client channels may also be orchestrated by n8n where appropriate;
- the public booking website talks to Resort Core directly for deterministic hotel operations.

Factual implementation/verification status is recorded only in `04_CURRENT_STATE.md`.

---

## 2. Resort Core responsibility

Resort OS is not required to become a provider-specific CRM/channel gateway.

Its active boundary includes authoritative hotel capabilities such as:
- public website booking contract;
- PMS / reception;
- room inventory and availability;
- rates and deterministic pricing;
- ReservationRequest / Reservation / Stay lifecycle;
- manager-recorded internal payment facts under the Three Crowns V1 manual-payment boundary;
- housekeeping / maintenance;
- staff interfaces and automation;
- owner/manager Command Center;
- audit, RBAC, realtime and operational reporting;
- controlled API/tool surface for n8n.

Generic automated acquiring/payment-provider integration is not an active Three Crowns V1 requirement. Generic Resort OS provider selection remains VALIDATE in canonical decision authority.

---

## 3. n8n responsibility

Where configured, n8n may:
- receive messages from ManyChat / API Green / Telegram / other channels;
- orchestrate AI extraction and dialogue;
- call Resort Core for authoritative hotel facts, availability, pricing and existing request/reservation/payment facts;
- create/read ReservationRequest through allowed Core APIs;
- send replies through connected channel providers;
- log normalized communication events to Core when useful for audit/control;
- hand a hot qualified lead/request to hotel management.

n8n remains an orchestration layer, not the hotel operational source of truth.

---

## 4. Three Crowns payment handoff

Approved active V1 boundary:
1. automation qualifies the guest and can create/read ReservationRequest;
2. manager reviews the request/quote;
3. manager decides the prepayment amount, terms and payment method;
4. manager collects the payment manually;
5. Resort OS records the manager-confirmed internal payment fact through controlled PMS/Core flows;
6. only the controlled human conversion can create guaranteed Reservation truth.

Automation must not claim that a room is booked before manager-confirmed Reservation truth exists.

This manual V1 decision does not resolve the generic Resort OS payment-provider/acquiring validation queue.

---

## 5. Security / truth boundary

n8n and AI must not:
- write directly to PostgreSQL;
- invent availability, price or policy;
- treat ReservationRequest as Reservation;
- choose or approve prepayment amount/method;
- represent an unconfirmed payment as received;
- create guaranteed reservations outside the controlled human conversion flow;
- check guests in/out without approved hotel actions;
- refund or mutate hotel money outside approved deterministic Core routes;
- gain permissions beyond the authorized user/service context.

Critical hotel logic remains deterministic and server-authoritative.

---

## 6. Existing direct provider code

Direct Telegram Sales/provider adapter code already present in the repository may remain as optional/reference implementation where `04_CURRENT_STATE.md` records it.

It is not an active V1 dependency and must not silently compete with the n8n architecture approved in D-019.

Provider credentials, production enablement and external-provider behavior require actual configuration/evidence; documentation alone is not proof of a working integration.

---

## 7. Active focus

Current active delivery priority is taken from `07_EXECUTION_PLAN_THREE_CROWNS.md`, which is itself subordinate to `04` and `05`.

At this stage the client-automation boundary should remain stable while delivery focuses on production migration/restore/staging/deployment gates and other evidence-backed remaining work.

Do not make generic payment-provider integration, NFC, or unspecified dining/store/access/QR/billiards/LED modules active merely because older planning text mentioned them.

NFC remains DEFERRED under D-021.
