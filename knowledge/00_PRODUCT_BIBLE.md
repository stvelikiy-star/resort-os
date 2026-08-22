# RESORT OS — PRODUCT BIBLE

Version: 1.0
Status: APPROVED
Qualifier: PRODUCT FOUNDATION
Canonical: YES
Document Type: Canonical Product Knowledge
Purpose: Define what Resort OS is, what product is being built, its approved product principles, capabilities and boundaries.

IMPORTANT:

This document describes the TARGET PRODUCT.

It does NOT prove that any capability is currently implemented.

TARGET ≠ CURRENT.

---

# 1. DOCUMENT AUTHORITY

This document is the canonical Product Bible of Resort OS.

It defines:

- product identity;
- product vision;
- target customer spectrum;
- core product principles;
- approved product capabilities;
- major product boundaries;
- strategic product direction.

It does NOT define:

- actual Current State;
- repository structure;
- programming language;
- framework;
- database;
- API implementation;
- deployment;
- actual integrations;
- implementation evidence.

Those belong to other canonical documents.

---

# 2. PRODUCT TRUTH

The following distinctions are mandatory:

APPROVED ≠ IMPLEMENTED

APPROVED CONCEPT ≠ IMPLEMENTED

PLANNED ≠ IMPLEMENTED

IMPLEMENTED ≠ VERIFIED

PROPOSED ≠ APPROVED

TARGET ARCHITECTURE ≠ CURRENT ARCHITECTURE

DOCUMENTED ≠ IMPLEMENTED

TEST FILE EXISTS ≠ TEST PASSED

PLANNED INTEGRATION ≠ WORKING INTEGRATION

MARKETING CLAIM <= VERIFIED PRODUCT CAPABILITY

Product documentation must never be used as evidence that functionality exists in the real system.

---

# 3. STATUS MODEL

Canonical project statuses:

VERIFIED FACT
= a fact about the real system, market, integration or configuration supported by evidence.

APPROVED
= explicitly accepted project rule or decision.

APPROVED CONCEPT
= accepted direction whose implementation/details may still vary.

PROPOSED
= proposal not yet accepted.

VALIDATE
= requires technical, product, market, legal, integration or customer validation.

IMPLEMENTED
= implementation exists but is not necessarily verified.

VERIFIED
= implemented capability that passed required checks and has evidence.

UNKNOWN
= insufficient information.

BLOCKED
= work or verification cannot continue because required access, information, evidence or decision is missing.

REJECTED
= consciously rejected.

PLANNED
= planned but not currently available.

Audit-specific statuses may additionally include:

PARTIAL

BROKEN

These do not automatically change Product approval status.

---

# 4. PRODUCT DEFINITION

Status: APPROVED

Resort OS is a universal hospitality operations platform designed to support different levels of hospitality complexity through one shared product foundation.

Target Customer Spectrum:

- Guest House;
- Small Hotel;
- Medium Hotel;
- Large Hotel;
- Resort;
- Resort & SPA;
- Multi-Property hospitality operations.

This spectrum defines product reach.

It does NOT define the first commercial ICP.

FIRST ICP:

VALIDATE.

---

# 5. PRODUCT VISION

Status: APPROVED

Core product direction:

ONE PLATFORM

ONE CORE

MODULAR ARCHITECTURE

SHARED CANONICAL DOMAIN MODEL

AI ADMINISTRATOR

ONE DEVICE → ENTIRE RESORT

Resort OS should not become a collection of unrelated hospitality applications.

The target is one coherent platform whose capabilities can expand with property complexity.

---

# 6. ONE PLATFORM / ONE CORE

Status: APPROVED

Guest House, Hotel, Resort and Resort & SPA should not automatically become separate products or independent codebases.

The product should share a common Core wherever domain semantics are genuinely shared.

Property complexity should be handled primarily through:

- configuration;
- modules;
- capabilities;
- roles;
- permissions;
- operational context.

A separate implementation may only be justified by explicit architectural/product evidence.

---

# 7. SHARED CANONICAL DOMAIN MODEL

Status: APPROVED

Resort OS should maintain a shared canonical understanding of major hospitality domain concepts.

Examples include:

- Property;
- Room;
- Room Type;
- Guest;
- Reservation Request;
- Reservation;
- Stay;
- Availability;
- Inventory;
- Pricing;
- Folio;
- Payment;
- Service;
- Resource;
- Task;
- Partner / Agent.

A Shared Canonical Domain Model does NOT require:

- one physical database;
- one table for everything;
- one service;
- one deployment unit.

Physical architecture is defined separately.

---

# 8. UNIVERSAL INSIDE → SIMPLE OUTSIDE

Status: APPROVED

Resort OS may be internally universal, but the user experience must remain appropriate to the property and user.

A Guest House should not be forced to operate an interface designed for a large Resort.

Visible functionality may depend on:

- property configuration;
- enabled modules;
- role;
- permissions;
- current workflow;
- operational context.

Product universality must not create unnecessary operational complexity.

---

# 9. PRODUCT CONFIGURATION MODEL

Status: APPROVED CONCEPT

The product should adapt to the property through configuration rather than requiring the customer to choose an entirely different application.

Potential configuration dimensions include:

- property characteristics;
- number of rooms;
- buildings/properties;
- enabled services;
- operational departments;
- staff roles;
- sales channels;
- guest-facing capabilities.

Exact onboarding flow:

VALIDATE.

---

# 10. CORE PRODUCT DOMAINS

Status: APPROVED CONCEPT

The target Resort OS product includes the following major domain areas:

- PMS / Reservations;
- Guest / Stay;
- Inventory / Availability;
- Pricing;
- Folio / Finance;
- Payments;
- Operations / Tasks;
- Housekeeping;
- Maintenance;
- Services / Resources;
- Partner / Agent;
- Guest CRM;
- Guest Portal;
- Dashboard / Command Center;
- AI Administrator;
- Omnichannel;
- Integrations;
- Multi-Property.

This is a target capability map.

It is NOT evidence that every module exists today.

Exact V1 composition:

VALIDATE.

---

# 11. SMART BOOKING BOARD

Status: APPROVED CONCEPT

Smart Booking Board is a key operational PMS interface.

Its target purpose is to provide staff with a practical operational view of accommodation occupancy and stay movement.

Target capabilities may include:

- reservation visibility;
- room assignment;
- room movement;
- stay modification;
- operational room/stay context.

Detailed UI behavior is not defined in this Product Bible.

Detailed Business Rules belong to:

01_DOMAIN_BUSINESS_RULES.md

Implementation architecture belongs to:

02_SYSTEM_ARCHITECTURE.md

---

# 12. RESERVATION REQUEST ≠ CONFIRMED RESERVATION

Status: APPROVED
Priority: CRITICAL

Reservation Request and Confirmed Reservation are distinct concepts.

Canonical product rule:

RESERVATION REQUEST
→ CHECK / CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

Human Confirmation is mandatory for final Reservation confirmation.

AI Administrator may create or assist with a Reservation Request.

AI Administrator must NOT independently perform final Reservation confirmation.

Automation or integrations must not silently bypass this boundary.

Detailed lifecycle rules belong to:

01_DOMAIN_BUSINESS_RULES.md

---

# 13. GUEST ≠ STAY

Status: APPROVED

Guest and Stay are distinct domain concepts.

A Guest represents the person/profile.

A Stay represents the operational accommodation event/context.

The product must not assume that Guest and Stay are the same entity.

Detailed relationships belong to the Domain Business Rules and System Architecture.

---

# 14. SPLIT STAY / PARTIAL ROOM MOVE

Status: APPROVED

Resort OS must support the product capability for Split Stay / Partial Room Move.

This means a Stay may require accommodation movement across different rooms/segments during the overall stay period.

The capability is approved.

Exact:

- data model;
- pricing behavior;
- folio behavior;
- inventory behavior;
- UX;
- operational transition rules

must be defined separately.

APPROVED CAPABILITY ≠ APPROVED IMPLEMENTATION MODEL.

---

# 15. UNIVERSAL DOMAIN CAPABILITIES

Status: APPROVED CONCEPT

Where business semantics genuinely overlap, Resort OS should prefer reusable domain capabilities rather than duplicated isolated implementations.

Potential reusable capabilities include:

- Task Engine;
- Service Engine;
- Resource / Scheduling capability;
- Partner / Agent capability;
- Notification capability;
- Audit capability.

Do NOT force unrelated workflows into one abstraction merely because they look technically similar.

Semantic correctness is more important than artificial reuse.

---

# 16. PARTNER / AGENT MANAGEMENT

Status: APPROVED CONCEPT

Resort OS should support Partner / Agent management.

Target capability includes traceability for:

- source attribution;
- associated Reservations;
- associated Guests/Stays where applicable;
- revenue attribution;
- commission history;
- settlement history;
- operational and financial traceability.

The following are NOT yet approved as universal rules:

- commission percentage;
- commission formula;
- settlement period;
- refund consequences;
- tax treatment;
- currency rules;
- payment rules.

These require Domain Business Rule decisions.

---

# 17. AI ADMINISTRATOR

Status: APPROVED
Priority: STRATEGIC

AI Administrator is a central product layer and strategic differentiator of Resort OS.

It is not intended to be merely an FAQ chatbot.

The product goal is to allow authorized users and guests to interact with Resort OS through natural language while preserving:

- real system data;
- permissions;
- Business Rules;
- security;
- Human Confirmation;
- auditability.

AI Administrator must operate over controlled Resort OS capabilities.

Detailed AI architecture and governance belongs to:

03_AI_ADMIN.md

---

# 18. AI ADMINISTRATOR — TWO PRIMARY CONTOURS

Status: APPROVED

AI Administrator has two primary product contours:

## AI Operations Administrator

For authorized internal users such as:

- owner;
- manager;
- administrator;
- reception;
- staff.

Target role:

understand operational questions and assist with permitted Resort OS workflows.

## AI Sales & Concierge

For guest/customer-facing communication.

Target role:

- understand inquiries;
- answer verified property questions;
- assist booking inquiry;
- collect booking parameters;
- check real availability through controlled capabilities;
- obtain real calculations;
- create Reservation Requests;
- assist existing guests;
- route service requests.

Potential channels include:

- Web — VALIDATE;
- Telegram — VALIDATE;
- WhatsApp — VALIDATE;
- Instagram — VALIDATE.

A target channel is NOT a claim of a working integration.

---

# 19. AI PRODUCT BOUNDARIES

Status: APPROVED

Core AI principles:

SOURCE OF OPERATIONAL TRUTH
=
RESORT OS CONTROLLED DOMAIN / INTEGRATION LAYER

Where an external system is explicitly designated as authoritative for a specific domain, Resort OS may retrieve that information through an approved controlled integration.

AI must not bypass Resort OS authorization, policy and controlled execution boundaries to access an external authoritative system directly.

AI_PERMISSION <= CURRENT_USER_PERMISSION

AI must not invent:

- availability;
- prices;
- Reservations;
- Guests;
- Stays;
- payments;
- orders;
- room states;
- operational facts.

Critical Business Rules must use deterministic logic where required.

AI must not replace authorization.

AI must not use unrestricted production database access as a generic business interface.

Core Resort OS operations must not depend entirely on AI.

---

# 20. GUEST PORTAL / QR

Status: APPROVED CONCEPT

Resort OS should provide a guest-facing digital access layer that can work without requiring installation of a native application.

Potential entry:

secure QR / guest web context.

Potential guest capabilities:

- property information;
- restaurant / room service;
- housekeeping request;
- towels / linen request;
- maintenance request;
- reception request;
- SPA / activities;
- service requests;
- request/order status tracking.

Guest access must use secure context.

A simple predictable URL such as:

/room/305

must not by itself be considered secure guest authorization.

Exact token/session architecture belongs to System Architecture.

---

# 21. GUEST REQUEST FLOW

Status: APPROVED CONCEPT

Target pattern:

GUEST
→ REQUEST
→ RESORT OS
→ RESPONSIBLE OPERATIONAL WORKFLOW
→ STATUS
→ COMPLETION

Examples:

Guest QR
→ Housekeeping Request
→ Task
→ Staff
→ Status
→ Completed

Guest QR
→ Maintenance Request
→ Ticket / Task
→ Assigned Staff
→ Status
→ Resolved

Exact workflow states require Domain Business Rules.

---

# 22. F&B / ROOM SERVICE

Status: APPROVED CONCEPT
Strategy: VALIDATE

Potential product scope includes:

- Restaurant;
- Dining Hall;
- Bar;
- Tables;
- Waiters;
- Menu;
- Room Service;
- Kitchen;
- KDS.

Target conceptual flow:

Guest
→ Menu
→ Cart
→ Order
→ Kitchen / KDS
→ Preparing
→ Ready
→ Delivery / Service
→ Guest
→ optional Folio / Payment

Order status, payment status and delivery status should not automatically be treated as one state.

Exact own-build scope is NOT approved.

Strategy must be selected through:

BUILD / INTEGRATE / HYBRID / DEFER.

---

# 23. DINING HALL

Status: APPROVED CONCEPT
Details: VALIDATE

Potential Resort-specific dining capabilities may include:

- breakfast;
- lunch;
- dinner;
- daily menu;
- meal plan;
- additional meals;
- visit tracking;
- portions;
- hall load.

Exact scope and Business Rules:

VALIDATE.

---

# 24. SERVICES / RESOURCES / SCHEDULING

Status: APPROVED CONCEPT

Resort OS should be capable of representing property services and operational resources.

Potential examples:

- SPA;
- massage;
- activities;
- transfer;
- equipment;
- venue;
- staff-dependent service.

Potential concepts:

- service;
- resource;
- capacity;
- duration;
- availability;
- schedule.

Exact resource and scheduling model:

TO BE DESIGNED through Domain and Architecture decisions.

---

# 25. HOUSEKEEPING

Status: APPROVED CONCEPT

Housekeeping is a core operational domain.

Target capabilities may include:

- cleaning workflow;
- room readiness;
- assignment;
- operational status;
- staff task handling;
- connection with arrivals/departures.

Exact status lifecycle:

DECISION REQUIRED.

---

# 26. MAINTENANCE

Status: APPROVED CONCEPT

Maintenance is a core operational domain.

Target capabilities may include:

- issue/request creation;
- assignment;
- priority;
- status;
- resolution;
- relationship to rooms/resources;
- operational history.

Exact lifecycle:

DECISION REQUIRED.

---

# 27. OPERATIONS / TASKS

Status: APPROVED CONCEPT

Resort OS should provide a coherent operational task capability.

Potential sources:

- staff;
- Guest Portal;
- AI Administrator;
- system events;
- integrations.

Exact Task lifecycle, SLA, escalation and assignment rules:

DECISION REQUIRED.

---

# 28. COMMAND CENTER / ONE DEVICE

Status: APPROVED CONCEPT

Management should be able to understand the current operational picture of the property from an allowed device.

Potential Command Center information:

- occupancy;
- arrivals;
- departures;
- rooms not ready;
- guest requests;
- housekeeping;
- maintenance;
- services;
- F&B status;
- staff tasks;
- alerts;
- selected financial/management indicators.

Primary product question:

WHAT IS HAPPENING IN THE PROPERTY RIGHT NOW?

Role-specific specialized interfaces remain valid.

ONE DEVICE does not mean ONE SCREEN FOR EVERY ROLE.

---

# 29. OMNICHANNEL

Status: APPROVED CONCEPT

Resort OS should support a channel-independent communication architecture.

Target pattern:

EXTERNAL CHANNEL
→ CHANNEL ADAPTER
→ OMNICHANNEL LAYER
→ IDENTITY / CONVERSATION CONTEXT
→ AI ADMINISTRATOR / RESORT OS CAPABILITIES

Potential channels require individual validation.

Do not claim working integrations without evidence.

---

# 30. INTEGRATION HUB

Status: APPROVED CONCEPT

Target integration pattern:

RESORT OS
↔ INTEGRATION HUB
↔ ADAPTERS
↔ EXTERNAL SERVICES

Potential integration categories:

- OTA;
- Channel Manager;
- payments;
- messaging;
- email;
- telephony;
- maps;
- accounting;
- fiscal systems;
- locks/access;
- IoT;
- POS/KDS;
- automation platforms.

Each integration requires verification of:

- official API;
- authentication;
- scopes;
- webhooks;
- rate limits;
- pricing;
- partner approval;
- regional restrictions;
- data policy;
- failure behavior.

PLANNED INTEGRATION ≠ WORKING INTEGRATION.

---

# 31. BUILD / INTEGRATE / HYBRID

Status: APPROVED

For significant capabilities, Resort OS may choose:

BUILD

INTEGRATE

HYBRID

DEFER

The choice must be based on:

- product differentiation;
- first ICP;
- operational criticality;
- implementation complexity;
- reliability;
- external API quality;
- cost;
- vendor dependency;
- regional availability;
- maintenance burden.

Do not assume every capability should be built internally.

Do not assume every capability should be delegated to an integration.

---

# 32. PAYMENTS

Status: APPROVED
Qualifier: PRODUCT REQUIREMENT
Implementation: VALIDATE

Resort OS must account for practical lawful payment scenarios required by target customers and guests.

This includes scenarios involving payments originating from Russia where lawful and technically supported.

This requirement does NOT establish:

- a specific provider;
- acquiring model;
- legal route;
- supported country;
- settlement currency;
- cross-border capability;
- fee;
- KYC model.

All such details require verification.

No payment provider or legal route may be invented.

---

# 33. MULTI-PROPERTY

Status: APPROVED CONCEPT
Details: VALIDATE

Multi-Property belongs to the target customer spectrum and long-term product architecture.

Potential concerns include:

- organization/property hierarchy;
- property isolation;
- central management;
- shared profiles where appropriate;
- cross-property operations;
- configuration inheritance;
- reporting.

Exact enterprise model is not approved.

Do not introduce unnecessary enterprise complexity before it is justified.

---

# 34. SIGNAGE

Status: VALIDATE
Scope: POST-V1 CANDIDATE

Potential signage capability may support:

- screens;
- screen groups;
- all-screen publishing;
- menus;
- announcements;
- schedules;
- events;
- images;
- welcome information;
- emergency information.

Signage is not currently established as a V1 requirement.

---

# 35. AUTOMATION

Status: APPROVED CONCEPT

Workflow automation may support Resort OS operations and integrations.

Automation platforms such as workflow engines may be useful for secondary orchestration.

Critical PMS/domain correctness must not depend on an external low-code automation layer as the only enforcement mechanism.

Critical Business Rules belong inside controlled Resort OS logic.

---

# 36. SECURITY PRODUCT PRINCIPLES

Status: APPROVED

Resort OS must be designed around:

- tenant isolation;
- property isolation;
- RBAC;
- resource-level authorization;
- least privilege;
- auditability;
- secret protection;
- input validation;
- session/API security;
- rate limiting where required;
- webhook verification;
- privacy;
- data integrity.

Frontend visibility is not an authorization boundary.

---

# 37. DATA INTEGRITY PRINCIPLES

Status: APPROVED

The product must protect against operational corruption such as:

- double booking;
- reservation conflicts;
- lost concurrent updates;
- inconsistent inventory;
- duplicate webhook processing;
- duplicate AI tool execution;
- duplicate payment processing;
- duplicate order creation;
- broken historical records.

Exact technical mechanisms belong to System Architecture.

---

# 38. AUDITABILITY

Status: APPROVED

Meaningful operational changes should be auditable.

Target audit context includes:

WHO

WHEN

TENANT

PROPERTY

ACTION

RESOURCE

BEFORE

AFTER

SOURCE

RESULT

Potential sources include:

USER

AI_ADMIN

API

INTEGRATION

AUTOMATION

SYSTEM

Exact technical schema belongs to System Architecture.

---

# 39. PRODUCT SCOPE CLASSIFICATION

Every significant capability should eventually be classified as:

V1 CORE

POST-V1

VALIDATE

DEFER

NOT PRODUCT SCOPE

Exact V1 composition is currently:

VALIDATE.

A capability being present in this Product Bible does not automatically make it V1.

---

# 40. FIRST ICP

Status: VALIDATE

Target Customer Spectrum is not equivalent to First ICP.

First ICP should be selected using evidence such as:

- pain severity;
- willingness to pay;
- implementation complexity;
- sales cycle;
- competition;
- required integrations;
- operational complexity;
- access to decision makers;
- demonstration value.

Do not invent First ICP.

---

# 41. COMMERCIAL PRODUCT PRINCIPLES

Status: APPROVED

Product Truth has priority over marketing.

Use the analysis chain:

FEATURE
→ TARGET CUSTOMER
→ PAIN
→ CURRENT WAY
→ PROPOSED WAY
→ BUSINESS VALUE
→ DEMO VALUE
→ WILLINGNESS TO PAY

Do not invent:

- ROI;
- market demand;
- conversion;
- revenue uplift;
- customer savings;
- pricing;
- SLA;
- integration availability.

AI Administrator positioning:

management of the property through natural language

rather than merely:

AI chatbot.

Guest QR should be positioned around structured guest access, requests and operational service flows.

Claims about upsell, labor savings or revenue impact require validation.

---

# 42. DEMONSTRATION PRINCIPLE

Status: APPROVED CONCEPT

Product demonstrations should prioritize end-to-end operational flows over disconnected screen tours.

Potential future demo flows:

Booking Inquiry
→ Availability
→ Calculation
→ Reservation Request
→ Human Confirmation
→ Reservation

Guest QR
→ Request
→ Staff Workflow
→ Status
→ Completion

Guest
→ Restaurant Order
→ Kitchen
→ Ready
→ Delivery

Manager
→ AI Administrator
→ Natural Language Request
→ Verified Context
→ Controlled Action
→ Result

Exact demo scope depends on First ICP and V1.

---

# 43. CURRENT STATE BOUNDARY

Status: APPROVED

This Product Bible does not describe actual implementation.

Current implementation truth belongs only in:

04_CURRENT_STATE.md

Therefore this document must never be used to claim that:

- code exists;
- module exists;
- integration works;
- test passes;
- deployment exists;
- AI exists;
- payment works;
- security control is implemented.

Product Bible = TARGET.

Current State = REALITY.

---

# 44. KNOWLEDGE RESPONSIBILITY

Canonical Knowledge architecture:

00_PRODUCT_BIBLE.md
= product definition and target

01_DOMAIN_BUSINESS_RULES.md
= approved domain behavior

02_SYSTEM_ARCHITECTURE.md
= target technical architecture

03_AI_ADMIN.md
= AI-specific architecture, authority and safety

04_CURRENT_STATE.md
= evidence-backed implementation reality

05_DECISIONS_AND_BACKLOG.md
= decisions, validation and future work

Documents must not silently take over each other's authority.

---

# 45. OPEN PRODUCT QUESTIONS

The following remain unresolved unless later explicitly approved:

- First ICP;
- exact V1 scope;
- detailed onboarding;
- detailed Reservation lifecycle;
- detailed Pricing rules;
- detailed Inventory model;
- detailed Folio model;
- payment implementation;
- Partner commission rules;
- Multi-Property details;
- exact F&B strategy;
- POS/KDS strategy;
- SPA scope;
- Signage scope;
- exact omnichannel channel implementation;
- exact integration portfolio.

These must remain:

VALIDATE

UNKNOWN

or

DECISION REQUIRED

as appropriate.

---

# 46. PRODUCT CHANGE CONTROL

This Product Bible is the approved baseline.

New ideas do not automatically become Product Truth.

Required flow:

NEW IDEA
→ PROPOSED / VALIDATE
→ ANALYSIS
→ DECISION
→ APPROVED / REJECTED

Only approved product changes should modify the canonical Product Bible.

Significant changes should increment the document version.

Do not modify Product Bible merely to make it match an incomplete implementation.

---

# 47. CANONICAL DEVELOPMENT PRINCIPLE

PRODUCT VISION
→ APPROVED PRODUCT BIBLE
→ BUSINESS RULES
→ TARGET ARCHITECTURE

IN PARALLEL:

REAL SYSTEM
→ AUDIT
→ CURRENT STATE

THEN:

TARGET
−
CURRENT
=
GAP

GAP
→ DECISION
→ BACKLOG
→ IMPLEMENTATION
→ TEST
→ EVIDENCE
→ VERIFIED

---

# FINAL PRODUCT PRINCIPLE

RESORT OS IS:

ONE PLATFORM.

ONE CORE.

MODULAR.

CONFIGURABLE.

DOMAIN-DRIVEN.

AI-ENABLED.

SECURE BY DESIGN.

EVIDENCE-DRIVEN.

UNIVERSAL INSIDE.

SIMPLE OUTSIDE.

The product must grow from Guest House simplicity to Resort complexity without becoming fragmented into unrelated systems.

AI must make Resort OS easier to operate, not less trustworthy.

Product documentation must describe the target truthfully.

Current State must describe implementation truthfully.

No feature is considered real merely because it is written here.
