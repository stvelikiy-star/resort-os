# 01_DOMAIN_BUSINESS_RULES.md

# RESORT OS — DOMAIN BUSINESS RULES

Version: 0.1
Qualifier: CANONICAL DOMAIN RULES — INITIAL BASELINE
Canonical: YES
Document Type: Domain Business Rules
Depends On: 00_PRODUCT_BIBLE.md

---

# 1. DOCUMENT PURPOSE

Этот документ является каноническим источником утверждённых Business Rules Resort OS.

Он определяет:

- business entities;
- domain terminology;
- lifecycle rules;
- state transitions;
- business constraints;
- cross-domain rules;
- invariants;
- human approval boundaries;
- правила, которые должны одинаково пониматься Product, Architecture, AI и Implementation.

Этот документ НЕ определяет:

- конкретные database tables;
- ORM models;
- API endpoints;
- programming language;
- framework;
- deployment architecture;
- конкретную физическую database architecture;
- UI implementation;
- неподтверждённые отраслевые предположения.

Техническая реализация определяется в:

02_SYSTEM_ARCHITECTURE.md

AI-specific rules определяются в:

03_AI_ADMIN.md

Фактическая реализация определяется в:

04_CURRENT_STATE.md

Решения, гипотезы и backlog определяются в:

05_DECISIONS_AND_BACKLOG.md

---

# 2. SOURCE OF AUTHORITY

Высший продуктовый источник:

00_PRODUCT_BIBLE.md

Business Rules в этом документе не должны противоречить утверждённому Product Bible.

При конфликте:

1. Не исправлять конфликт автоматически.
2. Зафиксировать его.
3. Определить источник противоречия.
4. Поместить вопрос в DECISION REQUIRED.
5. После явного решения обновить соответствующий canonical document.

---

# 3. STATUS MODEL

Каждое существенное Business Rule должно иметь статус.

APPROVED
= правило явно утверждено и является обязательным для целевой системы.

APPROVED CONCEPT
= направление утверждено, но точные правила ещё требуют определения.

PROPOSED
= предложенное правило, которое ещё не утверждено.

VALIDATE
= правило требует проверки через business analysis, CustDev, технический анализ, legal/compliance или другие источники.

UNKNOWN
= правило ещё не определено.

DECISION REQUIRED
= существуют варианты, но необходимо явное решение владельца продукта.

REJECTED
= вариант был рассмотрен и сознательно отклонён.

Критическое правило:

COMMON INDUSTRY PRACTICE ≠ APPROVED RESORT OS RULE

Нельзя превращать типичное поведение PMS/Hotel software в правило Resort OS без явного решения.

---

# 4. CORE DOMAIN TERMINOLOGY

## 4.1 PROPERTY

Status: APPROVED CONCEPT

Property представляет управляемый hospitality object в Resort OS.

Примеры целевого spectrum:

Guest House;
Hotel;
Resort;
Resort & SPA.

Точная модель:

Organization
→ Property
→ Building
→ Floor
→ Room

или другая hierarchy:

Status: UNKNOWN
Design: TO BE DESIGNED

Не считать эту hierarchy утверждённой до отдельного решения.

---

## 4.2 ROOM

Status: APPROVED CONCEPT

Room представляет accommodation resource, используемый в процессах availability, reservation и stay.

Точная модель:

Room;
Room Type;
Bed;
Unit;
Inventory Unit;
Out of Order;
Out of Service

Status: UNKNOWN
Design: TO BE DESIGNED

---

## 4.3 GUEST

Status: APPROVED

Guest представляет человека / guest profile.

Guest НЕ равен Reservation.

Guest НЕ равен Stay.

Один Guest потенциально может участвовать в нескольких Reservations и Stays в разные периоды.

Точные identity, deduplication, merge и profile rules:

Status: UNKNOWN
Decision: DECISION REQUIRED

---

## 4.4 RESERVATION

Status: APPROVED CONCEPT

Reservation представляет подтверждённое business commitment на размещение после прохождения утверждённого confirmation process.

Reservation должна быть отделена от Reservation Request.

Подробный lifecycle определяется далее.

---

## 4.5 RESERVATION REQUEST

Status: APPROVED

Reservation Request представляет запрос на потенциальное бронирование до Human Confirmation.

Reservation Request НЕ является Confirmed Reservation.

Создание Reservation Request само по себе не означает, что бронирование подтверждено.

---

## 4.6 STAY

Status: APPROVED

Stay представляет operational context фактического проживания Guest в объекте.

Guest и Stay являются разными concepts.

Reservation и Stay являются связанными, но не должны автоматически считаться одной entity.

Точные правила:

Reservation → Stay creation;
check-in;
no-show;
walk-in;
early arrival;
late departure;
Stay closure

Status: UNKNOWN
Decision: DECISION REQUIRED

---

## 4.7 SERVICE

Status: APPROVED CONCEPT

Service представляет услугу, доступную в рамках Property.

Service может быть связан с Guest/Stay и другими operational contexts там, где это требуется.

Конкретная taxonomy услуг:

Status: UNKNOWN
Design: TO BE DESIGNED

---

## 4.8 TASK

Status: APPROVED CONCEPT

Task представляет operational work item.

Потенциальные области:

Housekeeping;
Maintenance;
Guest Request;
Service Operation;
Internal Operation.

Не все процессы обязаны использовать одну идентичную Task model.

Конкретные Task lifecycle и assignment rules:

Status: UNKNOWN
Design: TO BE DESIGNED

---

## 4.9 PARTNER / AGENT

Status: APPROVED CONCEPT

Partner / Agent представляет внешний источник/партнёра, связанного с business activity объекта.

Целевая capability включает связь с:

source attribution;
reservations;
guests/stays where applicable;
revenue;
commission history;
settlement history.

Конкретные financial rules определяются отдельно.

---

# 5. RESERVATION REQUEST VS CONFIRMED RESERVATION

Status: APPROVED
Priority: CRITICAL

Утверждённый lifecycle boundary:

RESERVATION REQUEST
→ CHECK / CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

Это обязательная business boundary.

Reservation Request НЕ может автоматически считаться Confirmed Reservation.

AI может:

- принять запрос;
- определить booking intent;
- собрать необходимые данные;
- использовать разрешённые Resort OS capabilities для проверки;
- подготовить расчёт;
- создать Reservation Request;
- передать Request человеку для принятия решения.

AI НЕ может самостоятельно выполнить переход:

RESERVATION REQUEST
→ CONFIRMED RESERVATION

Этот переход требует Human Confirmation.

Автоматизация, integration или AI tool не должны обходить это правило.

---

# 6. RESERVATION LIFECYCLE

Status: APPROVED
Scope: PARTIAL — ONLY THE EXPLICITLY LISTED APPROVED BOUNDARIES
Remaining Rules: DECISION REQUIRED

Утверждено:

Reservation Request и Confirmed Reservation являются разными состояниями.

Human Confirmation обязателен для финального подтверждения Reservation.

НЕ определены:

точный набор statuses;
Request expiration;
hold behavior;
tentative reservation;
waitlist;
cancellation;
modification;
no-show;
walk-in;
group reservation;
overbooking policy;
inventory locking;
payment guarantee;
deposit requirements;
confirmation timeout;
cancellation fees.

Все перечисленные правила:

Status: UNKNOWN
Decision: DECISION REQUIRED

До их утверждения AI и Architecture не должны придумывать lifecycle самостоятельно.

---

# 7. AVAILABILITY & INVENTORY

Status: APPROVED CONCEPT
Rules: UNKNOWN

Availability является критической capability Resort OS.

Основной invariant:

Система не должна сознательно создавать противоречивое состояние inventory через обычные разрешённые операции.

Однако точная inventory model пока не утверждена.

Требуют решения:

availability calculation;
inventory unit;
room vs room-type inventory;
temporary holds;
reservation request effect on inventory;
confirmed reservation effect on inventory;
cancellation release;
room move effect;
Split Stay effect;
maintenance block;
out-of-order rooms;
overbooking policy;
concurrent booking handling;
external channel synchronization.

Status: UNKNOWN
Decision: DECISION REQUIRED

Нельзя проектировать окончательный Availability Engine до утверждения этих правил.

---

# 8. ROOM ASSIGNMENT

Status: APPROVED CONCEPT

Resort OS должен поддерживать связь проживания/бронирования с accommodation resource.

Однако необходимо отдельно определить:

когда Room назначается;
может ли Reservation существовать без конкретного Room;
может ли назначение происходить при check-in;
может ли Room меняться до arrival;
кто имеет право менять Room;
как изменение влияет на availability;
как хранится history.

Status: UNKNOWN
Decision: DECISION REQUIRED

---

# 9. SPLIT STAY / PARTIAL ROOM MOVE

Status: APPROVED
Priority: IMPORTANT

Split Stay / Partial Room Move является утверждённой capability Resort OS.

Система должна поддерживать сценарий, при котором проживание может быть разделено на периоды с разным accommodation assignment.

Conceptual example:

Stay:
Day 1–2 → Room A
Day 3–5 → Room B

Это capability-level rule.

Детальные Business Rules ещё не утверждены.

Требуют решения:

Stay segmentation model;
segment boundaries;
RoomAssignment model;
partial Room Move;
availability recalculation;
pricing recalculation;
folio consequences;
service linkage;
housekeeping consequences;
guest portal representation;
history;
audit;
concurrent modification;
rollback;
conflict detection.

Status: UNKNOWN
Decision: DECISION REQUIRED

Нельзя объявлять конкретный Split Stay algorithm утверждённым без отдельного решения.

---

# 10. PRICING

Status: UNKNOWN
Decision: DECISION REQUIRED

Pricing является core capability, но конкретные правила пока не утверждены.

Не определены:

base rate;
room-type pricing;
room-specific pricing;
seasonality;
weekday/weekend;
occupancy pricing;
adult pricing;
children pricing;
infant rules;
extra bed;
meal plans;
packages;
discounts;
promo codes;
manual override;
partner rates;
corporate rates;
long-stay pricing;
taxes;
fees;
currency conversion;
rounding;
price history;
price locking;
repricing after reservation modification;
Split Stay pricing.

Никакое из этих правил нельзя считать утверждённым только на основании industry practice.

---

# 11. CHILDREN / EXTRA BED / MEALS

Status: UNKNOWN
Decision: DECISION REQUIRED

Не утверждены:

age categories;
free-child rules;
child pricing;
infant rules;
extra bed eligibility;
extra bed pricing;
meal inclusion;
breakfast pricing;
meal plan logic;
child meal pricing;
package rules.

Эти правила должны быть определены после анализа реальных target properties и первого ICP.

---

# 12. FOLIO / CHARGES

Status: APPROVED CONCEPT
Rules: UNKNOWN

Resort OS должен иметь финансовый operational context, позволяющий связывать соответствующие charges с Guest/Stay/Reservation там, где это требуется.

Конкретная Folio model не утверждена.

Требуют решения:

one folio vs multiple folios;
guest folio;
company folio;
room folio;
charge posting;
service charges;
taxes;
discounts;
transfers;
split folio;
corrections;
voids;
refunds;
partial payments;
balance;
currency;
closing;
reopening;
audit.

Status: UNKNOWN
Decision: DECISION REQUIRED

---

# 13. PAYMENTS

Business Requirement Status: APPROVED
Detailed Business Rules: UNKNOWN / VALIDATE

Resort OS должен учитывать practical lawful payment scenarios целевых клиентов и гостей, включая сценарии, связанные с платежами, происходящими из России.

Но это НЕ определяет конкретный payment mechanism.

Требуют отдельного исследования:

provider;
acquiring;
legal route;
currencies;
settlement;
fees;
limits;
refunds;
KYC;
merchant requirements;
regional restrictions;
compliance;
API capabilities.

Нельзя утверждать конкретный payment route без evidence.

Payment status и Reservation status не должны автоматически считаться одной и той же business state.

Точная связь между:

payment;
deposit;
guarantee;
reservation confirmation;
folio balance

Status: UNKNOWN
Decision: DECISION REQUIRED

---

# 14. PARTNER / AGENT BUSINESS RULES

Status: APPROVED CONCEPT
Details: UNKNOWN

Resort OS должен поддерживать capability Partner / Agent Management.

Целевой business context включает:

source attribution;
associated Reservations;
associated Guests/Stays where applicable;
associated revenue;
commission history;
settlement history.

Не утверждены:

commission formula;
fixed vs percentage commission;
commission base;
gross vs net;
tax handling;
refund handling;
cancellation handling;
commission timing;
settlement period;
currency;
manual adjustment;
partner balance;
multi-property settlement.

Status: UNKNOWN
Decision: DECISION REQUIRED

---

# 15. OPERATIONS / TASKS

Status: APPROVED CONCEPT

Resort OS должен поддерживать operational work management.

Потенциальные источники Task:

Guest Request;
Housekeeping;
Maintenance;
Service;
Internal Operation;
AI-assisted workflow.

Не утверждены:

Task statuses;
priority model;
assignment;
reassignment;
SLA;
escalation;
dependencies;
recurrence;
completion evidence;
approval;
automatic closing.

Status: UNKNOWN
Design: TO BE DESIGNED

---

# 16. HOUSEKEEPING

Status: APPROVED CONCEPT

Housekeeping является operational domain Resort OS.

Потенциально должен учитывать:

room context;
Stay context;
room readiness;
cleaning tasks;
guest requests;
linen/towel requests;
staff assignment.

Точные room statuses и housekeeping lifecycle:

Status: UNKNOWN
Decision: DECISION REQUIRED

Не использовать автоматически стандартные PMS statuses без утверждения.

---

# 17. MAINTENANCE

Status: APPROVED CONCEPT

Maintenance является operational domain Resort OS.

Потенциально включает:

issue;
location/resource;
priority;
assignment;
status;
resolution;
history.

Не утверждены:

maintenance lifecycle;
severity model;
out-of-order consequences;
inventory consequences;
escalation;
preventive maintenance.

Status: UNKNOWN
Decision: DECISION REQUIRED

---

# 18. GUEST REQUESTS

Status: APPROVED CONCEPT

Guest может инициировать operational requests через доступные каналы Resort OS.

Potential flow:

GUEST
→ REQUEST
→ RESORT OS
→ OPERATIONAL PROCESS
→ STATUS
→ COMPLETION

Request должен быть связан с реальным Guest/Stay context там, где это необходимо.

Не утверждены:

request taxonomy;
status model;
SLA;
routing;
assignment;
escalation;
notification behavior.

Status: UNKNOWN
Design: TO BE DESIGNED

---

# 19. GUEST PORTAL / QR

Status: APPROVED CONCEPT

Guest Portal должен предоставлять гостю доступ только к разрешённым capabilities конкретного Property/Stay.

QR не должен быть простым небезопасным идентификатором вида:

/room/305

Доступ должен учитывать secure guest context.

Security principle:

Guest A не должен получать доступ к данным Guest B.

Stay A не должен давать доступ к Stay B без явного разрешения.

Точные правила:

token;
expiration;
revocation;
stay binding;
device/session behavior;
authentication fallback;
rate limiting

определяются в:

02_SYSTEM_ARCHITECTURE.md

---

# 20. F&B / ROOM SERVICE

Status: APPROVED CONCEPT
Implementation Strategy: VALIDATE

Resort OS может поддерживать:

Restaurant;
Dining Hall;
Bar;
Tables;
Waiters;
Menu;
Room Service;
Kitchen;
KDS.

Conceptual flow:

Guest / Staff
→ Menu
→ Cart / Order
→ Kitchen / KDS
→ Preparation
→ Ready
→ Delivery / Service
→ optional Charge / Folio / Payment

Order Status,
Payment Status
и
Delivery Status

не должны автоматически считаться одной state machine.

Конкретные lifecycle rules:

Status: UNKNOWN
Decision: DECISION REQUIRED

Full POS/KDS strategy:

BUILD / INTEGRATE / HYBRID / DEFER

Status: VALIDATE

---

# 21. SERVICES / RESOURCES / SCHEDULING

Status: APPROVED CONCEPT

Resort OS должен иметь возможность поддерживать services/resources, необходимые объекту.

Potential examples:

SPA;
activities;
transfers;
equipment;
facilities;
events;
other bookable services.

Нельзя считать, что все Services имеют одинаковую scheduling model.

Не утверждены:

capacity;
duration;
staff/resource requirements;
availability;
buffers;
cancellation;
pricing;
concurrency;
package rules.

Status: UNKNOWN
Design: TO BE DESIGNED

---

# 22. AI BUSINESS BOUNDARIES

Status: APPROVED
Priority: CRITICAL

SOURCE OF TRUTH = RESORT OS

AI не является источником operational truth.

AI не должен придумывать:

availability;
price;
Reservation;
Guest;
Stay;
Payment;
Order;
Room Status;
Task Status;
financial data;
operational data.

AI должен получать такие данные через разрешённые Resort OS tools/capabilities.

Permission invariant:

AI_PERMISSION <= CURRENT_USER_PERMISSION

AI может создавать Reservation Request.

AI не подтверждает финальную Reservation.

Critical и financial actions требуют Human-in-the-loop в соответствии с утверждёнными Business Rules.

Все значимые AI actions должны быть audit-capable.

Подробные AI rules:

03_AI_ADMIN.md

---

# 23. HUMAN-IN-THE-LOOP

Status: APPROVED CONCEPT

Human Confirmation является обязательной для:

final Reservation confirmation;

а также для других critical/financial operations, когда это будет определено утверждёнными Business Rules.

Точный список critical operations:

Status: UNKNOWN
Decision: DECISION REQUIRED

До определения этого списка AI не должен самостоятельно расширять свои полномочия.

---

# 24. AUDITABILITY

Status: APPROVED CONCEPT

Значимые business actions должны быть traceable.

Целевой audit context должен позволять определить:

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

Potential SOURCE values:

USER
AI_ADMIN
API
INTEGRATION
AUTOMATION
SYSTEM

Конкретная Audit architecture:

02_SYSTEM_ARCHITECTURE.md

Конкретный перечень audited events:

Design: TO BE DESIGNED

---

# 25. MULTI-PROPERTY

Status: APPROVED CONCEPT

Resort OS должен архитектурно учитывать Multi-Property / Hotel Group use cases.

Однако конкретные Business Rules пока не утверждены.

Требуют решения:

shared guest profiles;
property-specific guest data;
cross-property reservations;
central inventory;
central pricing;
staff access;
partner relationships;
financial separation;
reporting;
shared services;
cross-property stays.

Status: UNKNOWN
Validation: VALIDATE

---

# 26. BUSINESS INVARIANTS

Следующие invariants считаются базовыми.

## INVARIANT 1

Status: APPROVED

Reservation Request ≠ Confirmed Reservation.

## INVARIANT 2

Status: APPROVED

Final Reservation Confirmation requires Human Confirmation.

## INVARIANT 3

Status: APPROVED

Guest ≠ Stay.

## INVARIANT 4

Status: APPROVED

AI operational data must come from Resort OS or another explicitly verified source.

## INVARIANT 5

Status: APPROVED

AI permissions cannot exceed current user permissions.

## INVARIANT 6

Status: APPROVED

Product Target must not be represented as Current Reality.

## INVARIANT 7

Status: APPROVED

IMPLEMENTED does not automatically mean VERIFIED.

## INVARIANT 8

Status: APPROVED

Split Stay / Partial Room Move is a required product capability, but its detailed algorithm requires explicit Business Rules.

## INVARIANT 9

Status: APPROVED

Order Status, Payment Status and Delivery Status are conceptually separate states where F&B/order workflows are used.

## INVARIANT 10

Status: APPROVED

Critical Business Rules must not depend on LLM improvisation.

---

# 27. OPEN DOMAIN DECISIONS

The following require future explicit decisions.

## RESERVATIONS

- complete Reservation lifecycle;
- request expiration;
- cancellation;
- no-show;
- modification;
- walk-in;
- groups;
- inventory hold behavior;
- overbooking.

## STAY

- Stay creation;
- check-in;
- check-out;
- early/late behavior;
- Stay closure;
- room movement;
- Stay segmentation.

## INVENTORY

- inventory model;
- room vs room-type availability;
- locking;
- concurrent booking;
- maintenance blocks;
- external inventory synchronization.

## PRICING

- rate model;
- seasonality;
- children;
- meals;
- extra beds;
- packages;
- discounts;
- taxes;
- currency;
- rounding;
- repricing.

## FINANCE

- Folio model;
- charges;
- corrections;
- refunds;
- deposits;
- payment relationships;
- currencies.

## PARTNERS

- commissions;
- settlements;
- refunds;
- taxes;
- currencies.

## OPERATIONS

- Task lifecycle;
- Housekeeping lifecycle;
- Maintenance lifecycle;
- SLA/escalation.

## SERVICES

- resource scheduling;
- capacity;
- availability;
- cancellation;
- service pricing.

## MULTI-PROPERTY

- shared vs isolated data;
- central management;
- cross-property operations.

These are NOT implementation tasks until sufficient product/business analysis has been completed.

---

# 28. RULE FOR ADDING NEW BUSINESS RULES

A new Business Rule must follow:

QUESTION / PROBLEM
→ ANALYSIS
→ OPTIONS
→ PROPOSED RULE
→ REVIEW
→ EXPLICIT DECISION
→ APPROVED / REJECTED
→ CANONICAL UPDATE

AI must not skip:

EXPLICIT DECISION.

If the user explicitly approves a proposed rule, it may become APPROVED and be incorporated into the next canonical version.

---

# 29. RULE FOR TECHNICAL IMPLEMENTATION

Implementation must follow approved Business Rules.

Architecture may determine HOW a rule is implemented.

Architecture must not silently redefine WHAT the business rule means.

If technical constraints conflict with an APPROVED Business Rule:

1. Identify the conflict.
2. Explain evidence.
3. Explain technical impact.
4. Present alternatives.
5. Request an explicit product decision.

Do not silently change the rule to simplify implementation.

---

# 30. RELATION TO CURRENT STATE

This document describes approved DOMAIN TARGET RULES.

It does NOT prove that those rules exist in the current software.

Comparison must follow:

DOMAIN BUSINESS RULES
+
PRODUCT BIBLE
=
TARGET

REAL SYSTEM
=
CURRENT

TARGET − CURRENT
=
GAP

04_CURRENT_STATE.md must never be generated by copying this document.

Current State requires evidence from the real project.

---

# 31. VERSIONING

Current Version:

0.1

Reason:

The canonical structure is established, but many detailed Resort OS Business Rules remain intentionally UNKNOWN / DECISION REQUIRED.

This document should NOT be declared Version 1.0 until the critical V1 domain rules required by the selected ICP have been explicitly decided.

Future changes must preserve decision history where material.

---

# FINAL DOMAIN PRINCIPLE

DO NOT INVENT BUSINESS RULES.

DO NOT COPY INDUSTRY ASSUMPTIONS INTO CANONICAL KNOWLEDGE.

DO NOT LET TECHNICAL IMPLEMENTATION SILENTLY DEFINE PRODUCT BEHAVIOR.

For every important domain question distinguish:

WHAT IS APPROVED

WHAT IS PROPOSED

WHAT REQUIRES VALIDATION

WHAT IS UNKNOWN

WHAT REQUIRES A DECISION

Only explicitly approved rules become canonical Resort OS Business Rules.

