# THREE CROWNS — ACTIVE EXECUTION PLAN

Version: 1.3
Date: 2026-08-25
Status: ACTIVE
Scope: Current implementation order for «Три Короны»

Critical rule: implement only evidence-backed requirements. Unknown business rules remain UNKNOWN / DECISION REQUIRED.

## 1. Explicit freeze

NFC / wristband / internal-wallet work is DEFERRED and excluded from the active engineering queue until the owner explicitly reactivates it.

Existing NFC code is retained as dormant implementation evidence. No further NFC feature development, provider integration, UX expansion or production activation is part of the current plan.

## 2. Product priority — owner decision

The V1 product priority is now explicit:

1. **PMS chessboard is the primary daily operating surface.** It must support safe date changes, room moves, in-stay relocation, check-in/check-out and guest/reservation detail without corrupting inventory or history.
2. **Admin/PMS must be highly usable and multifunctional**, with the chessboard, reception, reservations, room history, operations, staff and internal finance connected to the same Resort Core truth.
3. **Public website must be a polished sales site**, with real availability/pricing/request creation from the same Resort Core data used by PMS.
4. **n8n owns client conversation automation** and hands hot qualified clients to management.

The website, PMS and n8n must never maintain separate copies of sellability/price/booking truth.

## 3. Client automation boundary — owner decision

Customer-channel work is orchestrated through **n8n**, not through provider-specific business logic inside Resort Core.

Current owner-selected channel path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- Telegram / other client channels may also be orchestrated through n8n where appropriate;
- website booking talks to Resort Core directly for deterministic availability/pricing/request creation.

Resort Core remains the source of operational truth and exposes controlled APIs/tools to n8n. n8n may orchestrate conversations, AI extraction/replies and channel delivery, but it must not bypass Core and write PostgreSQL directly.

### Sales handoff boundary

The automation objective is to produce a **hot, qualified client**, not to collect prepayment.

n8n / AI may:
- collect dates, guest count and contact data;
- use Resort Core for deterministic availability and current price facts;
- answer approved hotel questions using authoritative facts;
- create/read ReservationRequest;
- hand the qualified request to hotel management.

After handoff:
- the **manager decides the prepayment amount/terms and collects prepayment manually**;
- client automation does not create a payment link, choose a payment method, collect money or decide whether prepayment is sufficient;
- Resort OS may record the manager-confirmed internal payment/reservation facts for PMS and internal finance control;
- without manager-confirmed prepayment/reservation fact, automation must not tell the guest that the room is booked.

Core responsibilities for client automation:
- deterministic availability and pricing facts;
- create/read ReservationRequest;
- expose reservation/payment status facts only when they exist in Core;
- expose approved hotel facts required for replies;
- optional normalized communication/audit ingestion;
- idempotency and service authentication;
- deny AI/n8n direct authority to confirm payment, create a guaranteed reservation, check-in/check-out, refund or mutate hotel money.

Direct provider adapters already present in the repository may be retained as optional/reference code, but they are not an active dependency for V1 and must not distract from hotel operations, automation contracts or the public site.

## 4. Finance boundary — owner decision

V1 finance is **internal hotel control only**.

Resort OS may show and store internal facts already entered/confirmed by management, including:
- reservation value;
- manager-confirmed received payment/prepayment records;
- outstanding balance calculated from stored reservation/payment facts;
- payment method/provider reference if management records them;
- internal period/payment summaries.

Resort OS V1 does NOT need to:
- collect prepayment from the guest automatically;
- generate payment links/QR for the sales automation;
- choose the prepayment amount or payment method;
- integrate acquiring/webhooks as a prerequisite for launch;
- implement accounting profit, tax or revenue-recognition rules that have not been specified.

## 5. PMS chessboard mutation contract — P0

All chessboard mutations must be server-authoritative and transactional. The browser never edits booking truth optimistically without Core confirmation.

Supported P0 operations:
- move a future reservation to another room for the same dates;
- change future reservation check-in/check-out dates (resize/cut the block);
- relocate a CHECKED_IN guest from an effective date without rewriting already-lived room history;
- split one reservation into contiguous room-assignment segments when a guest changes room during the stay;
- check-in/check-out from the reservation/chessboard workflow;
- open room and reservation detail from the chessboard.

Safety invariants:
- every move/resize/relocation is one PostgreSQL transaction;
- reservation and affected room/inventory rows are locked before mutation;
- target-room overlap is rechecked inside the transaction;
- PostgreSQL `no_overlapping_active_room_blocks` remains the final double-booking guard;
- failure/conflict rolls back the entire mutation and leaves the original booking unchanged;
- past checked-in room history is never silently rewritten;
- every successful mutation creates AuditLog before/after evidence;
- same-dates room changes do not silently alter the stored reservation value;
- date/category changes must show deterministic Core pricing as a preview/delta, but price policy is not silently changed without explicit management confirmation;
- website availability sees the resulting inventory immediately from the same Core data.

The detailed implementation contract lives in `docs/PMS_CHESSBOARD_MUTATION_CONTRACT.md`.

## 6. Active engineering order

P0/P1 order:

1. **Transactional PMS chessboard mutations: move / resize / relocate / split / conflict-safe rollback.**
2. Chessboard interaction UX: drag/drop, resize handles, mutation preview, confirmation, conflict feedback and immediate realtime refresh.
3. Reservation/guest/room side panel connected to chessboard: check-in, check-out, contact, stay details, internal payment facts, tasks and audit history.
4. PMS daily management surface and cross-module navigation for owner/reception.
5. Housekeeping and maintenance operational control, staff assignment and history.
6. Internal hotel finance visibility from manager-entered/confirmed facts.
7. Owner Command Center and cross-module analytics.
8. Stable n8n/Core automation contracts for hot-lead qualification and handoff.
9. Public-site production completion: polished sales UX, owned media, room content, mobile booking and shared live availability/pricing.
10. AI Sales/Concierge through n8n over controlled Core tools only.
11. Whisper/audio staff intake and staff automation.
12. Production hardening, migrations, backup/restore, monitoring, staging, rollback and cutover.
13. Dining management after exact operational rules are confirmed.
14. Store management after ownership/accounting boundary is confirmed.
15. QR service points / access / billiards after exact operating rules/equipment are known.
16. LED content management after hardware/protocol inventory is known.

## 7. Work that may proceed without further owner input

- transactional room-assignment/date mutation engine using existing Reservation + InventoryBlock model and confirmed PostgreSQL overlap guard;
- drag/drop/resize PMS UX with server preview + explicit commit;
- dashboards and read-only analytics derived from existing canonical entities;
- richer search/filtering over existing PMS data;
- reservation/guest/payment/audit detail views where data already exists;
- internal finance summaries derived strictly from manager-recorded Payment/Reservation facts;
- housekeeping/maintenance assignment and status visibility using existing confirmed states;
- provider-neutral Inbox/Conversation/Message foundation when useful for audit/control, without making it a dependency on direct provider integration;
- guarded n8n/service contracts for qualification and handoff;
- deployment manifests, environment templates, health/readiness, logging, migrations, backup/restore and test scaffolding;
- public-site integration with existing Core availability/request endpoints;
- staff automation using existing confirmed task/status rules.

## 8. Work that must NOT be invented

Do not invent:

- automatic price-compensation policy when a manager changes dates/category/room;
- automated prepayment amount/terms or payment collection flow;
- cancellation/refund/no-show penalties;
- walk-in/group/waitlist rules;
- early-arrival/late-departure charges;
- exact dining entitlements/checklists beyond confirmed tariff facts;
- store ownership/accounting if not confirmed;
- entrance hardware/protocol;
- QR-toilet exact workflow if not confirmed;
- billiards pricing/booking rules;
- LED controller/device protocol;
- acquiring/payment-provider behavior unless the owner later explicitly reactivates that scope;
- production ManyChat/API Green credentials or provider-specific assumptions not supplied by the owner/integration;
- any production data or financial values not read from authoritative data.

## 9. Verification rule

Every change is classified as IMPLEMENTED until explicit test/build/runtime evidence exists. GitHub Actions infrastructure failures before any workflow step starts are not classified as code failures.

Development order:

KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE
