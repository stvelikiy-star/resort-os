# THREE CROWNS — MASTER SPECIFICATION

Version: 1.0-draft
Date: 2026-08-25
Status: ACTIVE BASELINE
Scope: Property-specific implementation profile for «Три Короны», Чолпон-Ата, Иссык-Куль
Canonical Role: Implementation specification subordinate to Product Bible / Domain Rules / Architecture

---

# 1. PURPOSE

Этот документ фиксирует практический контур системы «Три Короны» без смешения TARGET и CURRENT.

Он отвечает на вопросы:

- что именно строим для объекта «Три Короны»;
- какие модули обязательны;
- как они связаны;
- какие данные являются source of truth;
- какие роли существуют;
- какие workflows должны поддерживаться;
- что откладывается;
- какие данные ещё нельзя выдумывать и нужно получить от владельца/операционной команды.

Критическое правило:

CONFIRMED REQUIREMENT ≠ IMPLEMENTED CAPABILITY.

Фактическое состояние реализации продолжает определяться только через `04_CURRENT_STATE.md`.

---

# 2. PRODUCT POSITION FOR THREE CROWNS

Status: APPROVED / CONFIRMED REQUIREMENT

«Три Короны» строится не как набор отдельных приложений, а как единая Resort Operating System.

Основной принцип:

ONE PROPERTY → ONE CORE → ONE OPERATIONAL TRUTH.

Сайт, бронирование, PMS, персонал, задачи, коммуникации, столовая, магазин, QR/доступ, бильярд, LED и аналитика должны работать как модули одного ядра.

UX-принцип:

SIMPLE / FAST / ROLE-BASED.

Не использовать отдельные внешние CRM, task boards, project groups или другие сервисы как обязательный operational core.

Интеграции с внешними каналами допускаются только там, где они фактически необходимы для связи с клиентами/платежей/оборудования, но внутреннее состояние отеля должно принадлежать Resort OS.

---

# 3. IMPLEMENTATION PROFILE

Status: APPROVED FOR THREE CROWNS BASELINE

Целевая практическая реализация:

- Public Site: Next.js / TypeScript;
- Admin / PMS: Next.js / TypeScript;
- Backend Core: Python FastAPI;
- Database: PostgreSQL;
- Realtime PMS updates: WebSocket where required;
- Staff mobile interface: lightweight mobile web / Telegram WebApp where operationally useful;
- AI/automation: подключается после появления надёжного Core API;
- Critical business logic: только в Core/domain layer, не в LLM и не в внешней automation-схеме.

Физический стиль для первого рабочего релиза:

MODULAR MONOLITH FIRST.

Причина:

- один объект;
- быстрее разработка;
- проще deployment и support;
- меньше integration failure points;
- можно сохранить строгие domain boundaries без ранних microservices.

Микросервисы не являются целью V1.

---

# 4. MODULE MAP

## P0 — FOUNDATION / MUST WORK FIRST

1. Property / Room Inventory
2. Guests
3. Reservation Requests
4. Reservations
5. Stay / Check-in / Check-out
6. Availability
7. Pricing baseline
8. PMS Smart Grid
9. Authentication / RBAC
10. Audit Log
11. Operational Tasks

## P1 — CORE HOTEL OPERATIONS

12. Public Booking Flow
13. Housekeeping
14. Maintenance
15. Unified Communication Inbox / Answer Control
16. AI Sales & Concierge tools over Core API
17. Dining Hall management
18. Store management
19. Command Center

## P2 — PROPERTY SERVICES

20. QR Service Points
21. Access Control
22. Billiards / Resource Booking
23. LED Screen Control
24. Guest service requests

## P3 / DEFERRED

25. NFC wristband ecosystem
26. Internal guest wallet
27. NFC partner acquiring
28. Advanced multi-property capability

NFC is explicitly NOT a foundation dependency for current Three Crowns implementation.

---

# 5. FINANCIAL BOUNDARIES

## 5.1 HOTEL FINANCIAL CONTOUR

Status: CONFIRMED REQUIREMENT

Resort OS must support hotel-related financial state where applicable:

- reservation deposit / prepayment;
- reservation balance;
- payments recorded by hotel;
- store transactions if the store is operated by the hotel;
- future internal services if explicitly included.

Exact payment providers and fiscal implementation:

Status: DECISION REQUIRED / VALIDATE.

## 5.2 BEACH BAR

Status: CONFIRMED REQUIREMENT

Beach bar accepts payment independently.

Its customer payments are NOT part of Resort OS hotel financial ledger in the current scope.

Allowed Resort OS data may later include:

- point information;
- operating status;
- menu/information;
- contract/service metadata if needed.

No assumption about its revenue, commission or settlement may be made without a new explicit decision.

## 5.3 BEACH CAFE

Status: CONFIRMED REQUIREMENT

Beach cafe accepts payment independently.

Its customer payments are NOT part of Resort OS hotel financial ledger in the current scope.

## 5.4 NFC

Status: DEFERRED

NFC/wristband payment is optional future capability.

It must not block core PMS, booking, staff operations or guest service delivery.

---

# 6. CORE DOMAIN ENTITIES — THREE CROWNS V1

The first database/domain baseline must support at least:

## Property Structure

- Property
- Building / Zone
- Floor (if applicable)
- Room
- RoomType
- RoomFeature
- RoomState

Exact real property hierarchy:

Status: DATA REQUIRED.

## Guest / Stay

- Guest
- GuestContact
- ReservationRequest
- Reservation
- ReservationGuest
- Stay
- RoomAssignment
- RoomMove

Critical approved distinctions:

GUEST ≠ RESERVATION ≠ STAY.

## Inventory / Pricing

- InventoryBlock
- Availability context
- RatePlan
- RatePeriod / Season
- RoomRate
- PriceCalculation

Exact current room catalog, capacity and seasonal price matrix:

Status: DATA REQUIRED.

## Finance

- Payment
- PaymentAllocation
- Deposit
- Adjustment / Correction where required

Exact payment lifecycle:

Status: DECISION REQUIRED.

## Operations

- StaffUser
- Role
- Permission
- Task
- TaskAssignment
- TaskComment
- TaskAttachment
- HousekeepingJob
- MaintenanceTicket
- RoomInspection

## Communications

- ContactChannel
- Conversation
- Message
- Lead / BookingIntent link
- ConversationAssignment
- ResponseState

## Property Services

- ServicePoint
- QRPoint
- Resource
- ResourceBooking
- DisplayDevice / LED Screen
- DisplayPlaylist / Schedule

---

# 7. ROLES / RBAC BASELINE

Status: CONFIRMED BASELINE

Initial roles:

- OWNER
- MANAGER
- RECEPTION
- MAID
- TECHNICIAN
- STORE_STAFF
- DINING_STAFF
- CONTENT_MANAGER (only if needed for LED/content)
- GUEST

Previously discussed BEACH_PARTNER is not required for hotel payment flow after current business clarification.

If beach partners later need a non-financial information interface, a restricted role may be introduced separately.

Security invariant:

FRONTEND VISIBILITY ≠ AUTHORIZATION.

All write permissions must be verified server-side.

AI permission invariant:

AI_PERMISSION <= CURRENT_USER_PERMISSION.

---

# 8. ROOM STATE MODEL

Previously confirmed operational states:

- CLEAN
- DIRTY
- IN_INSPECTION
- TECH_BLOCK

Important design correction:

BOOKED must not be treated as the same type of state as physical room readiness.

Target V1 should separate:

A. ROOM OPERATIONAL STATE
- CLEAN
- DIRTY
- IN_INSPECTION
- TECH_BLOCK

B. OCCUPANCY / INVENTORY STATE
Derived from reservations, stays and blocks.

Examples displayed in PMS may include:

- RESERVED
- OCCUPIED
- ARRIVAL_TODAY
- DEPARTURE_TODAY
- AVAILABLE
- BLOCKED

Exact status names and precedence:

Status: TO BE FINALIZED BEFORE DB MIGRATION.

---

# 9. RESERVATION LIFECYCLE

Status: APPROVED CRITICAL BOUNDARY

Required boundary:

RESERVATION REQUEST
→ CHECK / PRICE CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION.

AI may create a request and prepare data.

AI may NOT autonomously perform final confirmation.

Exact lifecycle after confirmation must be finalized before implementation.

Required states to define include at minimum concepts for:

- request received;
- waiting manager action;
- confirmed;
- awaiting payment / deposit where applicable;
- cancelled;
- checked-in;
- checked-out;
- no-show if business requires it.

Exact enum names and transitions:

Status: DECISION REQUIRED.

---

# 10. PMS SMART GRID — REQUIRED UX

Status: CONFIRMED REQUIREMENT / PARTIAL RECOVERED PROTOTYPE

The PMS board is a primary operational screen.

Layout:

- rooms/resources on Y axis;
- calendar dates on X axis;
- reservations/stays/blocks rendered directly across date cells;
- sticky room column;
- horizontal scrolling;
- compact high-density layout;
- fast actions without unnecessary navigation.

Required time modes:

- Week
- Month

Day mode may be added if operationally useful.

## 10.1 REQUIRED FILTERS

Baseline filter groups:

Property location:
- building / zone;
- floor where applicable.

Room attributes:
- room type/category;
- capacity where needed.

Operational state:
- clean;
- dirty;
- inspection;
- technical block.

Occupancy / booking:
- free;
- reserved;
- occupied;
- arrival today;
- departure today;
- reservation request / unconfirmed;
- payment attention where payment state exists.

Source / workflow:
- booking source;
- assigned manager where applicable.

Filters must be composable, fast and removable in one action.

## 10.2 REQUIRED PMS ACTIONS

From the grid or reservation card:

- create reservation request;
- create reservation after authorized confirmation;
- open guest profile;
- open reservation;
- modify dates;
- change room assignment;
- support split stay / room move;
- check in;
- check out;
- record room readiness;
- create housekeeping task;
- create maintenance ticket;
- mark technical block;
- view payment state;
- view audit/history.

Drag-and-drop must not silently mutate critical reservation data without validation and explicit confirmation.

## 10.3 REALTIME

Initial load may use HTTP API.

Operational changes should propagate to active PMS screens through a realtime mechanism where needed.

Recovered prototype expects future `GET /api/v1/pms/grid`.

Previously discussed target also includes `/ws/pms/grid`.

Baseline decision:

- HTTP GET = initial snapshot / refresh;
- WebSocket = realtime incremental updates.

Implementation must remain correct even if realtime connection temporarily fails; manual/background refresh must restore truth.

---

# 11. HOUSEKEEPING

Status: CONFIRMED REQUIREMENT

Primary flow:

CHECK-OUT / ROOM NEEDS CLEANING
→ DIRTY
→ ASSIGNED TO MAID
→ CLEANING IN PROGRESS
→ RESULT / CHECKLIST / PHOTO IF REQUIRED
→ IN_INSPECTION
→ APPROVED
→ CLEAN.

Required maid interface:

- today queue;
- room;
- priority;
- status;
- checklist;
- comment;
- photo attachment where required;
- issue reporting.

Manager view:

- all rooms waiting cleaning;
- assigned/unassigned;
- progress;
- overdue;
- inspection queue;
- employee workload.

Exact checklist:

Status: DATA REQUIRED.

---

# 12. MAINTENANCE

Status: CONFIRMED REQUIREMENT

Required flow:

ISSUE REPORTED
→ TICKET
→ PRIORITY
→ ASSIGN TECHNICIAN
→ IN PROGRESS
→ FIXED / NEEDS FOLLOW-UP
→ CLOSED.

If issue prevents sale/use of the room:

ROOM → TECH_BLOCK.

Technical block must affect availability.

Required technician interface:

- queue;
- room/location;
- description;
- priority;
- attachments;
- history;
- status update.

Voice note → transcription → proposed ticket is a planned AI-assisted capability.

AI must not invent location, room or repair completion.

---

# 13. UNIFIED COMMUNICATION / ANSWER CONTROL

Status: CONFIRMED REQUIREMENT

Goal:

Owner/manager must be able to control incoming guest communication and unanswered leads from one operational view.

Target channels already discussed:

- Instagram Direct;
- WhatsApp;
- Telegram;
- Website booking/contact requests.

Required normalized data:

- channel;
- sender;
- conversation;
- message timestamp;
- last incoming message;
- last outgoing response;
- assigned operator;
- response state;
- booking intent / linked request;
- result status.

Manager control must support:

- new/unread;
- waiting for response;
- answered;
- overdue;
- potential booking;
- reservation request created;
- closed/lost where appropriate.

Exact SLA timing for “overdue”:

Status: DECISION REQUIRED.

External channel APIs are integration dependencies only; Resort OS owns normalized operational state.

---

# 14. AI SALES & CONCIERGE

Status: PLANNED AFTER CORE

AI is not the source of truth.

AI must use controlled Core tools for:

- availability;
- pricing;
- reservation request creation;
- reservation lookup;
- property information;
- guest/stay context where authorized;
- task/service request creation.

AI may:

- answer FAQs;
- collect booking intent;
- present verified availability;
- present deterministic prices;
- create Reservation Request;
- escalate to manager.

AI may not:

- invent free rooms;
- invent a price;
- claim payment success without evidence;
- confirm final reservation without Human Confirmation;
- bypass RBAC.

---

# 15. DINING HALL / СТОЛОВАЯ

Status: CONFIRMED MODULE / BUSINESS RULES NOT YET CAPTURED

Module is required.

No business rules may be invented before operational discovery.

Data required:

- whether meals are included in accommodation;
- meal plans;
- breakfast/lunch/dinner schedule;
- adult/child rules;
- guest entitlement source;
- how entrance is controlled today;
- whether external/non-resident guests are served;
- whether menu production, kitchen stock or only attendance must be managed;
- reporting required by owner.

Until answered, implementation scope remains OPEN.

---

# 16. STORE / МАГАЗИН

Status: CONFIRMED MODULE

Store should be managed inside Resort OS if it is hotel-operated.

Baseline capability:

- products;
- stock;
- stock movements;
- sale;
- shift/operator;
- payment method record;
- returns/corrections;
- daily totals;
- audit.

No forced NFC requirement.

Exact fiscal/cash register integration:

Status: VALIDATE / DATA REQUIRED.

---

# 17. QR SERVICE POINTS

Status: CONFIRMED MODULE

Required use case includes toilet QR.

Baseline concept:

QR → lightweight guest/service page → issue/request → task → responsible staff → status → management visibility.

Example issue categories may be configured only after owner/staff confirmation.

The exact toilet checklist/categories are not yet confirmed and must not be invented.

Security:

Public QR must not expose guest/private/internal data.

---

# 18. ACCESS CONTROL / ВХОД

Status: CONFIRMED MODULE / HARDWARE UNKNOWN

The system must be ready to control or validate access to required zones.

Exact access technology is not yet selected.

Possible technologies must NOT be chosen until existing/planned hardware is known.

Data required:

- controlled entrances/zones;
- who is allowed;
- current physical process;
- installed turnstile/lock/controller hardware if any;
- online/offline requirement;
- guest/staff/visitor differences.

---

# 19. BILLIARDS / RESOURCE BOOKING

Status: CONFIRMED MODULE / RULES UNKNOWN

Treat billiards as a managed resource, not as a hardcoded special-case calendar.

Need to capture:

- number of tables;
- operating hours;
- paid/free;
- tariff if paid;
- duration rules;
- reservation method;
- staff control;
- guest eligibility.

Implementation should reuse generic Resource / ResourceBooking where possible.

---

# 20. LED SCREEN MANAGEMENT

Status: CONFIRMED MODULE / HARDWARE UNKNOWN

Target capability:

- register display devices;
- assign screen/location;
- upload/select approved content;
- playlists;
- schedules;
- emergency/priority content where required;
- current playback status if supported by hardware;
- audit of content changes.

Supported media/protocol/player technology:

Status: DATA REQUIRED.

Do not choose vendor-specific architecture before hardware audit.

---

# 21. COMMAND CENTER

Status: CONFIRMED REQUIREMENT

Owner/manager needs one fast operational dashboard.

Required dashboard domains:

Hotel:
- occupancy;
- available inventory;
- arrivals;
- departures;
- rooms not ready;
- technical blocks.

Booking:
- new Reservation Requests;
- requests waiting action;
- confirmed reservations;
- payment attention when payment state exists.

Communications:
- unanswered conversations;
- overdue responses;
- channel distribution;
- booking leads.

Staff:
- housekeeping backlog;
- inspection backlog;
- maintenance tickets;
- overdue tasks;
- workload.

Property services:
- QR incidents;
- access events where available;
- resource bookings;
- LED device/content alerts where supported.

Finance:
- only verified hotel financial data;
- never include beach bar/cafe independent revenue unless future explicit integration is approved.

Dashboard must favor exceptions and actions over decorative analytics.

---

# 22. AUDIT / CONTROL

Status: REQUIRED

Critical writes must be traceable.

Audit fields should support:

- WHO;
- WHEN;
- ACTION;
- RESOURCE;
- BEFORE;
- AFTER;
- SOURCE;
- RESULT.

High-priority audit areas:

- reservation confirmation/modification/cancellation;
- room assignment;
- room state;
- technical blocks;
- payments/corrections;
- staff task status;
- access decisions where implemented;
- AI tool actions;
- LED content changes.

---

# 23. RELIABILITY / DATA INTEGRITY

P0 requirements:

- prevent overlapping confirmed reservations for the same inventory unit unless explicitly allowed by a future business rule;
- protect concurrent booking actions;
- idempotent critical commands where retries are possible;
- never use UI state as source of truth;
- backend validates all reservation and room mutations;
- technical block affects sellable availability;
- failed AI/integration action cannot be reported as success;
- reconnect/reload must restore correct PMS state from Core.

---

# 24. WHAT WE DO NOT BUILD FIRST

To keep implementation simple and fast, V1 does NOT start with:

- microservices;
- multi-property administration UI;
- NFC wallet;
- beach partner acquiring;
- advanced revenue management;
- complex IoT automation;
- separate CRM product;
- separate housekeeping SaaS;
- separate task platform;
- separate content-management SaaS for LED if simple internal control is technically possible.

---

# 25. DATA REQUIRED — MUST NOT BE INVENTED

The following facts must be collected from the owner/current operation and then entered into canonical data/specification.

## P0 DATA

1. Exact current room inventory:
   - room number/name;
   - building/zone;
   - floor;
   - room type;
   - capacity;
   - operational status.

2. Exact current room types and descriptions.

3. Actual pricing/rate periods:
   - dates/seasons;
   - room type/room rates;
   - occupancy rules;
   - child rules;
   - discounts if any.

4. Reservation operation:
   - what manager must verify before confirmation;
   - deposit/prepayment rule;
   - cancellation rule;
   - no-show rule;
   - early/late check-in/out policy;
   - current booking sources.

5. Staff list/roles needed for first pilot.

## P1 DATA

6. Housekeeping checklist and actual room cleaning workflow.

7. Maintenance priorities and who can TECH_BLOCK/unblock a room.

8. Dining hall real workflow.

9. Store real workflow / stock / cashier process.

10. Response-control SLA and manager escalation rule.

## P2 DATA / HARDWARE

11. QR toilet workflow and desired issue categories.

12. Entrance/access points and installed hardware.

13. Billiard tables/rules/pricing.

14. LED screens:
   - number;
   - locations;
   - model/controllers/player;
   - current content loading method;
   - network connectivity.

---

# 26. FIRST IMPLEMENTATION SLICE

Do not begin with every module simultaneously.

First executable vertical slice:

PROPERTY / ROOMS
→ AVAILABILITY
→ RESERVATION REQUEST
→ HUMAN CONFIRMATION
→ RESERVATION
→ PMS GRID.

This slice creates the operational backbone required by site, reception, AI and later staff modules.

## Acceptance Criteria

1. Real rooms exist in PostgreSQL.
2. PMS loads real data, not mock generator.
3. Manager can select dates and see actual availability.
4. System rejects overlapping confirmed occupancy for the same room under the approved rule.
5. Reservation Request is distinct from Confirmed Reservation.
6. Authorized manager can confirm a valid request.
7. PMS immediately reflects confirmed reservation.
8. TECH_BLOCK removes a room from sellable availability for affected dates/state rules.
9. Every critical operation is auditable.
10. Reloading the UI reproduces the same truth from PostgreSQL.

---

# 27. IMMEDIATE DEVELOPMENT ORDER

1. Freeze/reconcile current recovery baseline.
2. Finalize room/property schema using real inventory.
3. Finalize reservation lifecycle states.
4. Implement PostgreSQL schema and migrations.
5. Implement FastAPI Core endpoints.
6. Connect recovered PMS UI to live API.
7. Add authentication/RBAC for OWNER / MANAGER / RECEPTION.
8. Verify concurrency and booking conflict prevention.
9. Connect public booking flow as Reservation Request only.
10. Then build Housekeeping + Maintenance.
11. Then Unified Communications + AI tools.
12. Then Dining Hall + Store.
13. Then QR / Access / Billiards / LED.
14. NFC remains deferred until explicit owner decision.

---

# 28. NEXT REQUIRED INPUT

The next engineering blocker is not another design document.

It is real operational data for the P0 core.

Minimum input package:

A. ROOM LIST
B. CURRENT RATES / SEASONS
C. CURRENT RESERVATION RULES

If these are unavailable immediately, engineering may still create the schema/API skeleton, but no production availability or pricing data may be invented.
