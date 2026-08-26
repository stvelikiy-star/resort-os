# RESORT OS — DECISIONS AND BACKLOG

Version: 0.2
Lifecycle: ACTIVE
Canonical: YES
Document Type: Decisions, Validation Queue & Product Backlog

Depends On:
- 00_PRODUCT_BIBLE.md
- 01_DOMAIN_BUSINESS_RULES.md
- 02_SYSTEM_ARCHITECTURE.md
- 03_AI_ADMIN.md
- 04_CURRENT_STATE.md for factual implementation evidence only

---

# 1. DOCUMENT PURPOSE AND AUTHORITY

This document is the canonical register of:
- approved and rejected decisions;
- open decisions;
- validation questions;
- backlog priorities;
- dependencies and blockers.

It is NOT Product Bible, Domain Rules, System Architecture, AI specification or Current State.

Canonical responsibility:
- `00_PRODUCT_BIBLE.md` = WHAT PRODUCT WE WANT;
- `01_DOMAIN_BUSINESS_RULES.md` = HOW THE BUSINESS MUST BEHAVE;
- `02_SYSTEM_ARCHITECTURE.md` = HOW THE TARGET SYSTEM SHOULD BE STRUCTURED;
- `03_AI_ADMIN.md` = HOW AI OPERATES INSIDE RESORT OS;
- `04_CURRENT_STATE.md` = WHAT ACTUALLY EXISTS, supported by evidence;
- `05_DECISIONS_AND_BACKLOG.md` = WHAT HAS BEEN DECIDED / WHAT REMAINS OPEN / WHAT SHOULD BE DONE NEXT.

Property-specific documents `06`, `07` and `08` are subordinate/supporting documents. They may elaborate approved decisions, requirements and execution order but cannot independently redefine canonical Product, Domain, Architecture, AI or Current State truth.

---

# 2. STATUS MODEL

Use explicit statuses only:

- APPROVED — decision accepted.
- APPROVED CONCEPT — direction accepted; exact details may remain open.
- PROPOSED — proposed, not accepted.
- VALIDATE — research/evidence required.
- UNKNOWN — insufficient information.
- DECISION REQUIRED — explicit owner/product decision required.
- PLANNED — accepted into plan, not implemented.
- IMPLEMENTED — implementation exists, verification may still be absent.
- VERIFIED — required checks/evidence exist.
- BLOCKED — cannot continue without missing input/access/decision/dependency.
- RESOLVED — historical blocker/question has been resolved; retain for traceability.
- REJECTED — consciously rejected.
- PARTIAL — partial implementation/compliance.
- BROKEN — existing capability does not meet required behavior.
- DEFERRED — consciously outside the active implementation queue.

Product truth invariants:

`APPROVED != IMPLEMENTED`

`IMPLEMENTED != VERIFIED`

`TARGET != CURRENT`

`DOCUMENTED != IMPLEMENTED`

`TEST EXISTS != TEST PASSED`

`PLANNED INTEGRATION != WORKING INTEGRATION`

`MARKETING CLAIM <= VERIFIED PRODUCT CAPABILITY`

Documentation changes cannot close an implementation GAP.

---

# 3. PRIORITY MODEL

- P0 — blocker, security/data-integrity/fundamental correctness.
- P1 — high-value V1/core workflow/dependency.
- P2 — important but not immediate blocker.
- P3 — improvement/future optimization.
- VALIDATE — priority cannot be set safely before research.
- DEFER — consciously postponed.

Next-task selection must consider product correctness, security, data integrity, critical business rules, dependencies, V1/operational/commercial value, implementation risk and verification feasibility. Prefer one bounded P0/P1 task at a time unless tasks are inseparable.

---

# 4. APPROVED PRODUCT DECISIONS

## D-001 — ONE PLATFORM / ONE CORE
Status: APPROVED
Area: Product Architecture

Resort OS develops as one platform with a shared Core and modular architecture. Do not create independent Guest House / Hotel / Resort / Resort & SPA products without separate evidence-backed justification.

## D-002 — SHARED CANONICAL DOMAIN MODEL
Status: APPROVED
Area: Domain Architecture

Use a shared canonical domain model for consistent domain concepts. This does not require one physical database or one physical service.

## D-003 — UNIVERSAL INSIDE → SIMPLE OUTSIDE
Status: APPROVED
Area: Product / UX

Internal platform universality must not create one overloaded interface for everyone. Capability exposure depends on configuration, enabled modules, role, permissions and context.

## D-004 — RESERVATION REQUEST != CONFIRMED RESERVATION
Status: APPROVED
Area: Reservations

ReservationRequest is distinct from Confirmed Reservation.

## D-005 — HUMAN CONFIRMATION FOR FINAL RESERVATION
Status: APPROVED
Area: Reservations / AI Safety

Approved lifecycle:

`RESERVATION REQUEST -> CHECK / CALCULATION -> HUMAN CONFIRMATION -> CONFIRMED RESERVATION`

AI cannot bypass Human Confirmation.

## D-006 — GUEST != STAY
Status: APPROVED
Area: Domain Model

Guest and Stay are different domain concepts.

## D-007 — SPLIT STAY / PARTIAL ROOM MOVE
Status: APPROVED
Area: PMS / Stay

Split Stay / Partial Room Move is a required capability. Generic product implementation detail remains architecture/domain dependent even if a property implementation already exists.

## D-008 — AI ADMINISTRATOR AS CENTRAL PRODUCT LAYER
Status: APPROVED
Area: AI / Product

AI Administrator is a central product layer and strategic differentiator of Resort OS.

## D-009 — TWO AI CONTOURS
Status: APPROVED
Area: AI

1. AI Operations Administrator.
2. AI Sales & Concierge.

## D-010 — AI PERMISSION BOUNDARY
Status: APPROVED
Area: AI / Security

`AI_PERMISSION <= CURRENT_USER_PERMISSION`.

## D-011 — RESORT OS AS OPERATIONAL SOURCE OF TRUTH
Status: APPROVED
Area: AI / Architecture

AI is not the operational source of truth. Operational data must come from Resort OS or another explicitly designated authoritative source.

## D-012 — CONTROLLED AI TOOLS
Status: APPROVED
Area: AI Architecture

AI performs operational actions only through controlled tools/functions and Resort OS application/domain boundaries. Unrestricted production database access is not a generic AI interface.

## D-013 — DETERMINISTIC CRITICAL BUSINESS LOGIC
Status: APPROVED
Area: Architecture / AI

Critical calculations, permissions, validations and state transitions must not depend on LLM improvisation.

## D-014 — PARTNER / AGENT CAPABILITY
Status: APPROVED CONCEPT
Area: Product

Resort OS should support Partner / Agent traceability across source attribution, reservations, guests/stays where applicable, revenue, commission history and settlement history. Exact commission/settlement rules remain unapproved.

## D-015 — PAYMENT BUSINESS REQUIREMENT
Status: APPROVED
Area: Payments

Resort OS must account for practical lawful payment scenarios of target customers/guests, including scenarios related to payments originating from Russia. This does NOT approve a provider, acquiring route or cross-border mechanism.

Generic implementation status: VALIDATE.

## D-016 — BUILD / INTEGRATE / HYBRID
Status: APPROVED
Area: Architecture / Product

For significant capabilities, valid strategies are BUILD / INTEGRATE / HYBRID / DEFER. Exact choice requires analysis.

## D-017 — CORE MUST NOT REQUIRE AI TO FUNCTION
Status: APPROVED
Area: Architecture

Core operational capabilities must function without mandatory AI dependency where applicable. AI failure must not imply total PMS failure.

## D-018 — IMPLEMENTED != VERIFIED
Status: APPROVED
Area: Product Truth / QA

Implementation becomes VERIFIED only with required evidence.

---

# 5. APPROVED THREE CROWNS PROPERTY DECISIONS

These decisions are property/V1 decisions for Three Crowns. They do not automatically resolve generic Resort OS product questions for every future property.

## D-019 — THREE CROWNS CLIENT AUTOMATION BOUNDARY
Status: APPROVED
Area: Three Crowns / Client Automation

Approved active channel architecture:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- other client channels may be orchestrated through n8n where appropriate;
- public booking website calls Resort Core directly for deterministic hotel operations.

n8n/AI objective is a hot qualified lead and controlled handoff. It may use Core facts and create/read ReservationRequest but must not write PostgreSQL directly, invent availability/price, confirm payment, create guaranteed Reservation outside controlled human conversion, check-in/out, refund or mutate hotel money.

Current factual implementation belongs only in `04_CURRENT_STATE.md`.

## D-020 — THREE CROWNS MANAGER-MANUAL PREPAYMENT BOUNDARY
Status: APPROVED
Area: Three Crowns / Payments / V1

For active Three Crowns V1:
- manager decides prepayment amount, terms and method;
- manager collects payment manually;
- Resort OS records manager-confirmed internal payment facts;
- automation does not choose amount/method, generate a payment link, collect money or decide sufficiency;
- automated acquiring/provider integration is not a V1 launch gate.

This property decision does NOT resolve generic provider/acquiring/cross-border validation under D-015 and the generic Payment Validation Queue.

## D-021 — THREE CROWNS NFC DEFERRED
Status: APPROVED / DEFERRED
Area: Three Crowns / NFC

NFC/wristband/internal-wallet work is excluded from the active Three Crowns V1 queue. Dormant source/schema evidence may remain. Reactivation requires a new explicit owner decision.

## D-022 — THREE CROWNS PMS CHESSBOARD PRIMARY DAILY SURFACE
Status: APPROVED
Area: Three Crowns / PMS / UX

The PMS chessboard is the primary daily operating surface for Three Crowns. It must remain connected to the same Resort Core truth as reception, operations, finance and public availability. Exact factual implementation status is owned only by `04_CURRENT_STATE.md`.

---

# 6. CURRENT PROJECT REALITY

Canonical implementation reality is maintained only in:

`04_CURRENT_STATE.md`

This document may cite that reality for decisions/prioritization but must not reproduce a competing Current State snapshot.

---

# 7. HISTORICAL BASELINE BLOCKER

## B-001 — CURRENT STATE BASELINE ESTABLISHED
Status: RESOLVED
Area: Project Baseline

Historical problem: at Knowledge-bootstrap time there was insufficient real-project evidence to establish Current State.

Resolution:
- the real `stvelikiy-star/resort-os` repository exists and is readable;
- implementation evidence, schema, tests/workflows and deployment artifacts are available;
- `04_CURRENT_STATE.md` is populated and is the only canonical factual implementation owner;
- exact verified executable baselines and verification evidence are recorded there.

B-001 must never again be used as an active blocker unless the actual repository/evidence becomes unavailable and `04_CURRENT_STATE.md` explicitly records that condition.

---

# 8. CONTINUOUS CURRENT STATE AUDIT

Status: ACTIVE
Execution: EVIDENCE-DRIVEN

Current State is established, not a future bootstrap task.

After every meaningful implementation change:

`IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> UPDATE 04_CURRENT_STATE.md`

Periodic audit should continue to cover technology stack, project structure, domain/data model, reservations/stays/inventory/pricing/finance/operations/security/RBAC/API/integrations/tests/deployment and AI implementation where present.

---

# 9. GAP ANALYSIS RULE

`APPROVED TARGET - VERIFIED CURRENT STATE = GAP`

A GAP is not automatically an immediate backlog item. Classify it as V1 REQUIRED / VALIDATE / DEFER / POST-V1 / DECISION REQUIRED / NOT PRODUCT SCOPE.

---

# 10. GENERIC DOMAIN DECISION QUEUES

Three Crowns-specific approved decisions do not silently resolve these generic Resort OS queues.

## Reservations — DECISION REQUIRED
Validate/decide generic lifecycle, request expiration, cancellation, modification, no-show, walk-in, groups, waitlist, holds, overbooking, confirmation timeout and deposit/guarantee relationship.

## Stay — DECISION REQUIRED
Validate/decide generic Stay creation/closure, check-in/out, early/late behavior, no-show relationship, room moves, Split Stay segmentation and history.

## Inventory — DECISION REQUIRED
Validate/decide generic inventory unit/model, availability, holds, maintenance/out-of-order blocks, concurrency/conflict behavior, external synchronization and overbooking.

## Pricing — DECISION REQUIRED
Validate/decide generic rate model, seasonality, weekday/weekend, occupancy/adult/child/extra-bed/meal/package pricing, discounts/promos/partners, taxes/fees/currencies/rounding, price locking/repricing and Split Stay pricing.

## Finance — DECISION REQUIRED
Validate/decide generic folio model, charges, payment relationships, deposits, refunds, corrections/voids, split folio/transfers, currencies, balances, closing/reopening and audit.

## Partners — DECISION REQUIRED
Validate/decide commission formula/base, fixed vs percentage, refund/cancellation consequences, tax treatment, settlement period/currency, manual adjustments and partner balance.

## Operations — DECISION REQUIRED
Validate/decide generic Task/SLA/escalation/priority/assignment/reassignment/completion lifecycles and generic Housekeeping/Maintenance/Guest Request states. Property implementations do not automatically become universal product rules.

## Services — DECISION REQUIRED
Validate/decide taxonomy, resource/capacity/duration/availability, staff/buffers, pricing, cancellation, packages and concurrency.

## Multi-Property — VALIDATE / DECISION REQUIRED
Validate organization/property hierarchy, shared vs isolated Guest data, cross-property operations, permissions, finance separation, configuration inheritance, reporting, shared services and Partner relationships. Do not create enterprise complexity without evidence.

---

# 11. AI DECISION QUEUE

Status: VALIDATE / DECISION REQUIRED

Still requires decisions/evidence for provider/model strategy, fallback, tool runtime, agent specialization, conversation storage/memory/retrieval, property knowledge, prompt versioning, observability/evaluation, risk classification, detailed Human Confirmation matrix, generic financial action policy, privacy/retention, cost controls and rate limits.

Approved AI boundaries D-008..D-013 remain mandatory while these implementation choices are open.

---

# 12. OMNICHANNEL VALIDATION QUEUE

Status: VALIDATE per channel

WEB / TELEGRAM / WHATSAPP / INSTAGRAM must each be validated for official API, auth/scopes, webhooks, capabilities, rate limits, pricing, regional availability, policy restrictions, identity linking and operational suitability.

Three Crowns D-019 approves its orchestration architecture but does not convert every generic provider/channel integration into a universally VERIFIED product integration.

---

# 13. PAYMENT VALIDATION QUEUE

Status: VALIDATE
Priority: HIGH BEFORE GENERIC PAYMENT-PROVIDER IMPLEMENTATION

Research target countries, merchant location, guest payment-origin scenarios, providers/acquiring, currencies/settlement, fees, KYC, merchant requirements, API/webhooks/refunds/limits/regional restrictions/compliance/legal constraints.

Do not select a provider from assumptions.

Three Crowns D-020 intentionally uses manager-manual prepayment for its active V1 and therefore does not require provider selection before that property V1 launch. This does not promote generic payment-provider implementation from VALIDATE.

---

# 14. INTEGRATION VALIDATION QUEUE

Status: VALIDATE UNTIL VERIFIED

Potential categories: OTA, Channel Manager, payments, messaging, email, telephony, maps, accounting, fiscal systems, locks/access, IoT, POS/KDS, SPA systems and automation platforms.

For each external system verify official documentation, API/auth/scopes/webhooks/rate limits/pricing/partner requirements/regional availability/data ownership/failure behavior.

---

# 15. F&B / SIGNAGE / PHYSICAL-SERVICE QUEUES

F&B: VALIDATE. Determine V1 relevance, first-ICP demand, build/integrate value, integration availability and operational complexity before BUILD / INTEGRATE / HYBRID / DEFER.

Signage: VALIDATE / POST-V1 CANDIDATE unless evidence changes priority.

Dining/store/access/QR/billiards/LED exact business rules must not be invented. Property-specific work requires explicit rules/equipment/protocol evidence.

---

# 16. FIRST ICP

Status: VALIDATE
Priority: HIGH

The broad Target Customer Spectrum exists, but FIRST ICP is not approved. Validate pain severity, willingness to pay, implementation complexity, sales cycle, competition, integrations, operational complexity, decision-maker accessibility and demonstration value.

Result should inform FIRST ICP and generic V1 REQUIRED SCOPE.

---

# 17. GENERIC V1 SCOPE

Status: DECISION REQUIRED

Generic Resort OS V1 must be coherent, sellable, useful, safe, demonstrable and implementable, but exact universal V1 cannot be inferred from the full Product Bible. It depends on FIRST ICP, Current State, Gap Analysis, dependencies, commercial validation and implementation cost.

Three Crowns has a property-specific active V1 execution boundary under D-019..D-022; that does not automatically become the generic Resort OS V1 definition.

---

# 18. COMMERCIAL VALIDATION

Status: VALIDATE

For significant capabilities use:

`FEATURE -> TARGET CUSTOMER -> PAIN -> CURRENT WAY -> PROPOSED WAY -> BUSINESS VALUE -> DEMO VALUE -> WILLINGNESS TO PAY`

Do not invent ROI, market demand, pricing, conversion, customer savings or revenue uplift.

---

# 19. DEMO BACKLOG PRINCIPLE

Status: APPROVED CONCEPT

Demonstrations should show end-to-end operational flows, not disconnected screens. Potential examples include booking request -> availability -> calculation -> Human Confirmation -> Reservation, guest request -> task -> staff -> completion, and AI natural-language request -> verified context -> controlled tool -> result.

Exact demo flows depend on scope/ICP and must respect Current State evidence.

---

# 20. IMPLEMENTATION AND VERIFICATION GATES

Before significant implementation know, as applicable:
- WHY / WHAT;
- approved business rule;
- Current State;
- Target State;
- dependencies/risks;
- acceptance criteria;
- verification method.

If critical information is absent: BLOCKED or DECISION REQUIRED.

After implementation, do not automatically promote IMPLEMENTED to VERIFIED. Evidence may include tests, integration/permission/negative tests, runtime behavior, data-integrity/security checks and manual acceptance where required.

---

# 21. CANONICAL CHANGE RULES

Product Bible changes:
`NEW IDEA -> PROPOSED / VALIDATE -> ANALYSIS -> DECISION -> APPROVED / REJECTED -> UPDATE 00`

Domain rule changes:
`QUESTION -> ANALYSIS -> OPTIONS -> PROPOSED -> EXPLICIT DECISION -> APPROVED / REJECTED -> UPDATE 01`

Architecture changes:
`PROBLEM -> REQUIREMENTS -> CONSTRAINTS -> OPTIONS -> TRADE-OFFS -> DECISION -> UPDATE 02 IF CANONICAL`

AI capability changes:
`BUSINESS NEED -> APPROVED RULE -> RISK -> TOOL/PERMISSION/HUMAN-CONFIRMATION DESIGN -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED -> ENABLEMENT`

Do not rewrite canonical target documents merely to hide a GAP or match an incomplete implementation.

---

# 22. DEFERRED / NOT YET DECIDED

Do not treat the following as mandatory generic V1 merely because they appear in vision: full POS/KDS, advanced Signage/SPA, IoT/locks, advanced Multi-Property, enterprise functionality, every omnichannel integration, every payment scenario, advanced automation or complex revenue management.

Each capability needs a scope decision.

---

# 23. CURRENT KNOWLEDGE BASELINE

Current canonical baseline:
- `00_PRODUCT_BIBLE.md` — ACTIVE canonical product target;
- `01_DOMAIN_BUSINESS_RULES.md` — ACTIVE canonical domain rules;
- `02_SYSTEM_ARCHITECTURE.md` — ACTIVE canonical target architecture;
- `03_AI_ADMIN.md` — ACTIVE canonical AI rules;
- `04_CURRENT_STATE.md` — ESTABLISHED and continuously evidence-updated factual implementation state;
- `05_DECISIONS_AND_BACKLOG.md` — ACTIVE canonical decisions/validation/backlog register.

Supporting Three Crowns documents:
- `06_THREE_CROWNS_MASTER_SPEC.md` — subordinate property implementation specification;
- `07_EXECUTION_PLAN_THREE_CROWNS.md` — supporting execution plan;
- `08_CLIENT_AUTOMATION_N8N_BOUNDARY.md` — supporting decision extract.

There is no active “wait for real project evidence” bootstrap phase. The real repository exists. Work proceeds from verified Current State to the next evidence-backed GAP/priority.

---

# 24. CANONICAL DEVELOPMENT LOOP

`PRODUCT VISION -> APPROVED PRODUCT BIBLE -> APPROVED BUSINESS RULES -> TARGET ARCHITECTURE`

Parallel factual lane:

`REAL CODE / SYSTEM -> AUDIT -> EVIDENCE -> CURRENT STATE`

Then:

`TARGET - CURRENT = GAP -> DECISION -> BACKLOG -> PLAN -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> UPDATE CURRENT STATE -> NEXT PRIORITY`

Human approval remains mandatory wherever canonical Product/Domain/AI rules require it.

---

# 25. FINAL BACKLOG PRINCIPLE

DO NOT IMPLEMENT RANDOMLY.

DO NOT TURN EVERY IDEA INTO V1.

DO NOT TURN EVERY GAP INTO P0.

DO NOT INVENT CURRENT STATE.

DO NOT MARK IMPLEMENTED AS VERIFIED WITHOUT EVIDENCE.

DO NOT CHANGE PRODUCT TARGET TO MATCH AN INCOMPLETE IMPLEMENTATION.

DO NOT ALLOW TECHNICAL CONVENIENCE TO SILENTLY REDEFINE BUSINESS RULES.

Every meaningful next step must answer:
- what problem is being solved;
- why now;
- what is approved;
- what is currently verified;
- what is the GAP;
- what decision is required;
- what priority applies;
- what will count as VERIFIED.
