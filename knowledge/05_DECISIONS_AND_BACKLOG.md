# RESORT OS — DECISIONS AND BACKLOG

Version: 0.1
Lifecycle: ACTIVE
Canonical: YES
Document Type: Decisions, Validation Queue & Product Backlog

Depends On:
- 00_PRODUCT_BIBLE.md
- 01_DOMAIN_BUSINESS_RULES.md
- 02_SYSTEM_ARCHITECTURE.md
- 03_AI_ADMIN.md

---

# 1. DOCUMENT PURPOSE

Этот документ является рабочим реестром:

- принятых решений;
- открытых решений;
- вопросов, требующих validation;
- архитектурных решений;
- product decisions;
- domain decisions;
- AI decisions;
- технических исследований;
- будущего backlog;
- приоритетов;
- зависимостей;
- блокеров.

Этот документ НЕ является:

Product Bible;
Domain Business Rules;
System Architecture;
AI specification;
Current State.

Он отвечает на вопросы:

WHAT HAS BEEN DECIDED?

WHAT IS NOT DECIDED?

WHAT MUST BE VALIDATED?

WHAT SHOULD BE DONE NEXT?

---

# 2. DOCUMENT RESPONSIBILITY

Разделение ответственности Knowledge:

00_PRODUCT_BIBLE.md
= WHAT PRODUCT WE WANT

01_DOMAIN_BUSINESS_RULES.md
= HOW THE BUSINESS MUST BEHAVE

02_SYSTEM_ARCHITECTURE.md
= HOW THE TARGET SYSTEM SHOULD BE STRUCTURED

03_AI_ADMIN.md
= HOW AI OPERATES INSIDE RESORT OS

04_CURRENT_STATE.md
= WHAT ACTUALLY EXISTS

05_DECISIONS_AND_BACKLOG.md
= WHAT MUST BE DECIDED / VALIDATED / DONE NEXT

---

# 3. STATUS MODEL

Использовать только явные статусы.

APPROVED
= решение принято.

APPROVED CONCEPT
= направление принято, детали ещё могут измениться.

PROPOSED
= предложение ожидает решения.

VALIDATE
= требуется исследование или проверка.

UNKNOWN
= информации недостаточно.

DECISION REQUIRED
= требуется явное решение владельца продукта.

PLANNED
= принято в план, но не реализовано.

IMPLEMENTED
= реализовано, но ещё не обязательно проверено.

VERIFIED
= реализация прошла необходимые проверки и имеет evidence.

BLOCKED
= работа не может продолжаться без недостающих данных, доступа, решения или зависимости.

REJECTED
= решение сознательно отклонено.

PARTIAL
= частичная реализация/соответствие.

BROKEN
= существующая capability не выполняет требуемое поведение.

---

# 4. PRODUCT TRUTH

Критические правила:

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

Нельзя закрывать GAP изменением документации.

---

# 5. PRIORITY MODEL

P0
= критический blocker, безопасность, data integrity, fundamental product correctness или невозможность продолжать работу.

P1
= высокая ценность для V1, core workflow или критическая dependency.

P2
= важная capability, но не обязательный immediate blocker.

P3
= improvement / optimization / future enhancement.

VALIDATE
= приоритет нельзя корректно определить до исследования.

DEFER
= сознательно отложено.

---

# 6. DECISION RECORD FORMAT

Каждое значимое решение должно по возможности фиксироваться в формате:

ID:

TITLE:

DATE:

STATUS:

AREA:

CONTEXT:

PROBLEM:

OPTIONS:

DECISION:

RATIONALE:

CONSEQUENCES:

DEPENDENCIES:

AFFECTED DOCUMENTS:

EVIDENCE:

OWNER:

NEXT ACTION:

Не все поля обязаны быть заполнены немедленно.

Неизвестные данные должны оставаться UNKNOWN.

---

# 7. APPROVED PRODUCT DECISIONS

## DECISION D-001

TITLE:
ONE PLATFORM / ONE CORE

STATUS:
APPROVED

AREA:
Product Architecture

DECISION:

Resort OS развивается как единая платформа с общим Core и модульной архитектурой.

Не создавать независимые продукты для:

Guest House;
Hotel;
Resort;
Resort & SPA

без отдельного доказанного основания.

---

## DECISION D-002

TITLE:
SHARED CANONICAL DOMAIN MODEL

STATUS:
APPROVED

AREA:
Domain Architecture

DECISION:

Resort OS использует Shared Canonical Domain Model для согласованного понимания основных domain concepts.

Это не требует одной database или одного physical service.

---

## DECISION D-003

TITLE:
UNIVERSAL INSIDE → SIMPLE OUTSIDE

STATUS:
APPROVED

AREA:
Product / UX

DECISION:

Внутренняя универсальность платформы не должна приводить к перегруженному одинаковому интерфейсу для всех типов объектов.

Функциональность должна зависеть от:

configuration;
enabled modules;
role;
permissions;
context.

---

## DECISION D-004

TITLE:
RESERVATION REQUEST ≠ CONFIRMED RESERVATION

STATUS:
APPROVED

AREA:
Reservations

DECISION:

Reservation Request является отдельным состоянием от Confirmed Reservation.

---

## DECISION D-005

TITLE:
HUMAN CONFIRMATION FOR FINAL RESERVATION

STATUS:
APPROVED

AREA:
Reservations / AI Safety

DECISION:

Final Reservation Confirmation требует Human Confirmation.

Approved lifecycle:

RESERVATION REQUEST
→ CHECK / CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

AI не может самостоятельно обходить этот переход.

---

## DECISION D-006

TITLE:
GUEST ≠ STAY

STATUS:
APPROVED

AREA:
Domain Model

DECISION:

Guest и Stay являются разными domain concepts.

---

## DECISION D-007

TITLE:
SPLIT STAY / PARTIAL ROOM MOVE

STATUS:
APPROVED

AREA:
PMS / Stay

DECISION:

Split Stay / Partial Room Move является требуемой capability Resort OS.

Конкретная implementation model ещё не утверждена.

---

## DECISION D-008

TITLE:
AI ADMINISTRATOR AS CENTRAL PRODUCT LAYER

STATUS:
APPROVED

AREA:
AI / Product

DECISION:

AI Administrator является central product layer and strategic differentiator Resort OS.

---

## DECISION D-009

TITLE:
TWO AI CONTOURS

STATUS:
APPROVED

AREA:
AI

DECISION:

AI Administrator имеет два основных product contours:

1. AI Operations Administrator
2. AI Sales & Concierge

---

## DECISION D-010

TITLE:
AI PERMISSION BOUNDARY

STATUS:
APPROVED

AREA:
AI / Security

DECISION:

AI_PERMISSION <= CURRENT_USER_PERMISSION

AI не получает больше полномочий, чем текущий пользователь/context.

---

## DECISION D-011

TITLE:
RESORT OS AS OPERATIONAL SOURCE OF TRUTH

STATUS:
APPROVED

AREA:
AI / Architecture

DECISION:

AI не является operational source of truth.

Operational data должна поступать из Resort OS или другого явно определённого authoritative source.

---

## DECISION D-012

TITLE:
CONTROLLED AI TOOLS

STATUS:
APPROVED

AREA:
AI Architecture

DECISION:

AI должен выполнять operational actions через controlled tools/functions и Resort OS domain/application layer.

Unrestricted production database access не является generic AI business interface.

---

## DECISION D-013

TITLE:
DETERMINISTIC CRITICAL BUSINESS LOGIC

STATUS:
APPROVED

AREA:
Architecture / AI

DECISION:

Critical Business Rules не должны зависеть от LLM improvisation.

Deterministic logic должна использоваться для критических calculations, permissions, validations и state transitions.

---

## DECISION D-014

TITLE:
PARTNER / AGENT CAPABILITY

STATUS:
APPROVED CONCEPT

AREA:
Product

DECISION:

Resort OS должен учитывать Partner / Agent management с traceability по:

source attribution;
reservations;
guests/stays where applicable;
revenue;
commission history;
settlement history.

Детальные commission/settlement rules ещё не утверждены.

---

## DECISION D-015

TITLE:
PAYMENT BUSINESS REQUIREMENT

STATUS:
APPROVED

AREA:
Payments

DECISION:

Resort OS должен учитывать practical lawful payment scenarios целевых клиентов и гостей, включая сценарии, связанные с платежами, происходящими из России.

Это НЕ является утверждением конкретного provider, acquiring route или cross-border mechanism.

Implementation:

VALIDATE.

---

## DECISION D-016

TITLE:
BUILD / INTEGRATE / HYBRID

STATUS:
APPROVED

AREA:
Architecture / Product

DECISION:

Для значимых capabilities допускаются стратегии:

BUILD;
INTEGRATE;
HYBRID;
DEFER.

Конкретный выбор принимается после анализа.

---

## DECISION D-017

TITLE:
CORE MUST NOT REQUIRE AI TO FUNCTION

STATUS:
APPROVED

AREA:
Architecture

DECISION:

Core operational Resort OS capabilities должны работать без обязательной зависимости от AI там, где это технически и продуктово применимо.

AI failure не должен автоматически означать total PMS failure.

---

## DECISION D-018

TITLE:
IMPLEMENTED ≠ VERIFIED

STATUS:
APPROVED

AREA:
Product Truth / QA

DECISION:

Наличие реализации не означает VERIFIED.

VERIFIED требует соответствующих проверок и evidence.

---

# 8. CURRENT PROJECT REALITY

Canonical implementation reality is maintained in:

04_CURRENT_STATE.md

This document may reference Current State when prioritizing decisions and backlog, but it must not redefine Current State.

# 9. CURRENT BLOCKER

## BLOCKER B-001

TITLE:
CURRENT STATE NOT ESTABLISHED

STATUS:
BLOCKED

AREA:
Project Baseline

PROBLEM:

Невозможно корректно определить фактический GAP между Target Product и Existing Implementation без evidence существующего проекта.

REQUIRED INPUT:

real project source;
repository/archive;
configuration where appropriate;
database/migrations/schema where available;
tests;
relevant technical documentation.

RESULT WHEN RESOLVED:

04_CURRENT_STATE.md

---

# 10. REQUIRED FUTURE CURRENT STATE AUDIT

Status: PLANNED
Execution: BLOCKED

Когда реальный проект станет доступен, выполнить:

REAL PROJECT
→ AUDIT
→ EVIDENCE
→ 04_CURRENT_STATE.md
→ TARGET VS CURRENT
→ GAP

Audit должен установить как минимум:

technology stack;

project structure;

domain implementation;

database/data model;

reservation capabilities;

guest/stay capabilities;

inventory;

pricing;

finance;

operations;

security;

RBAC;

tenant/property isolation;

API;

integrations;

tests;

deployment evidence;

AI capabilities if present.

---

# 11. GAP ANALYSIS RULE

GAP определяется только как:

APPROVED TARGET
−
VERIFIED CURRENT STATE
=
GAP

Не считать GAP автоматически immediate backlog item.

Каждый GAP должен быть классифицирован:

V1 REQUIRED

VALIDATE

DEFER

POST-V1

DECISION REQUIRED

NOT PRODUCT SCOPE

---

# 12. NEXT-TASK SELECTION RULE

После появления Current State следующая задача должна выбираться не по принципу:

"что интереснее сделать".

Приоритет учитывать:

1. Product correctness
2. Security
3. Data integrity
4. Critical Business Rules
5. Dependencies
6. V1 product value
7. Operational value
8. Commercial relevance
9. Implementation risk
10. Verification feasibility

Выбирается одна следующая P0/P1 задача, если нет причины формировать пакет взаимозависимых задач.

---

# 13. DOMAIN DECISION QUEUE — RESERVATIONS

Status:
DECISION REQUIRED

Необходимо определить:

Reservation lifecycle;

Reservation Request lifecycle;

request expiration;

cancellation;

modification;

no-show;

walk-in;

group reservations;

waitlist;

inventory hold behavior;

overbooking policy;

confirmation timeout;

deposit/guarantee relationship.

Не утверждать значения автоматически.

---

# 14. DOMAIN DECISION QUEUE — STAY

Status:
DECISION REQUIRED

Необходимо определить:

Stay creation;

check-in;

check-out;

early arrival;

late departure;

no-show relationship;

Stay closure;

Room Move;

Split Stay segmentation;

history.

---

# 15. DOMAIN DECISION QUEUE — INVENTORY

Status:
DECISION REQUIRED

Необходимо определить:

inventory unit;

room vs room-type inventory;

availability calculation;

temporary holds;

maintenance blocks;

out-of-order;

concurrency;

conflict handling;

external synchronization;

overbooking behavior.

---

# 16. DOMAIN DECISION QUEUE — PRICING

Status:
DECISION REQUIRED

Необходимо определить:

rate model;

seasonality;

weekday/weekend;

occupancy pricing;

adult/child pricing;

extra beds;

meal plans;

packages;

discounts;

promo codes;

partner rates;

taxes;

fees;

currencies;

rounding;

price locking;

repricing;

Split Stay pricing.

---

# 17. DOMAIN DECISION QUEUE — FINANCE

Status:
DECISION REQUIRED

Необходимо определить:

Folio model;

charges;

payment relationship;

deposits;

refunds;

corrections;

voids;

split folio;

transfers;

currencies;

balance;

closing/reopening;

audit.

---

# 18. DOMAIN DECISION QUEUE — PARTNERS

Status:
DECISION REQUIRED

Необходимо определить:

commission formula;

commission base;

fixed vs percentage;

refund consequences;

cancellation consequences;

tax treatment;

settlement period;

currency;

manual adjustments;

partner balance.

---

# 19. DOMAIN DECISION QUEUE — OPERATIONS

Status:
DECISION REQUIRED

Необходимо определить:

Task lifecycle;

priority;

assignment;

reassignment;

SLA;

escalation;

completion;

Housekeeping statuses;

Maintenance statuses;

Guest Request statuses.

---

# 20. DOMAIN DECISION QUEUE — SERVICES

Status:
DECISION REQUIRED

Необходимо определить:

service taxonomy;

resource model;

capacity;

duration;

availability;

staff requirements;

buffers;

pricing;

cancellation;

packages;

concurrency.

---

# 21. MULTI-PROPERTY DECISION QUEUE

Status: VALIDATE
Decision: DECISION REQUIRED

Необходимо определить:

organization/property hierarchy;

shared vs isolated Guest data;

cross-property operations;

central permissions;

financial separation;

configuration inheritance;

reporting;

shared services;

Partner relationships.

Не создавать enterprise complexity без подтверждённой необходимости.

---

# 22. AI DECISION QUEUE

Status: VALIDATE
Decision: DECISION REQUIRED

Необходимо определить:

LLM provider;

model strategy;

fallback;

tool runtime;

single-agent vs internal specialization;

conversation storage;

memory strategy;

retrieval;

property knowledge;

prompt versioning;

AI observability;

AI evaluation;

risk classification;

Human Confirmation matrix;

financial action policy;

privacy;

retention;

cost controls;

rate limits.

---

# 23. OMNICHANNEL VALIDATION QUEUE

Каждый channel проверяется отдельно.

## WEB

Status:
VALIDATE

## TELEGRAM

Status:
VALIDATE

## WHATSAPP

Status:
VALIDATE

## INSTAGRAM

Status:
VALIDATE

Для каждого проверить:

official API;

authentication;

permissions/scopes;

webhooks;

message capabilities;

rate limits;

pricing;

regional availability;

policy restrictions;

identity linking;

operational suitability.

---

# 24. PAYMENT VALIDATION QUEUE

Status:
VALIDATE
Priority:
HIGH BEFORE PAYMENT IMPLEMENTATION

Необходимо исследовать:

target countries;

merchant location;

guest payment origin scenarios;

providers;

acquiring;

currencies;

settlement currencies;

fees;

KYC;

merchant requirements;

API;

webhooks;

refunds;

limits;

regional restrictions;

compliance;

legal constraints.

Нельзя выбирать provider на основании предположений.

---

# 25. INTEGRATION VALIDATION QUEUE

Potential categories:

OTA;

Channel Manager;

payments;

messaging;

email;

telephony;

maps;

accounting;

fiscal systems;

locks/access;

IoT;

POS/KDS;

SPA systems;

automation platforms.

Status for each:

VALIDATE UNTIL VERIFIED.

Для каждого external system проверять:

official documentation;

API;

auth;

scopes;

webhooks;

rate limits;

pricing;

partner requirements;

regional availability;

data ownership;

failure behavior.

---

# 26. F&B DECISION QUEUE

Status:
VALIDATE

Potential scope:

Restaurant;

Dining Hall;

Bar;

Tables;

Waiters;

Menu;

Room Service;

Kitchen;

KDS.

Необходимо определить:

V1 relevance;

first ICP demand;

own-build value;

integration availability;

operational complexity.

Strategy:

BUILD / INTEGRATE / HYBRID / DEFER

Decision:
NOT YET MADE.

---

# 27. SIGNAGE DECISION

Status: VALIDATE
Scope: POST-V1 CANDIDATE

Potential capability:

screen groups;

all screens;

menu;

announcement;

schedule;

event;

image;

welcome;

emergency information.

Не считать V1 requirement без validation.

---

# 28. FIRST ICP

Status:
VALIDATE
Priority:
HIGH

Target Customer Spectrum уже определён широко.

Но FIRST ICP ещё не должен считаться утверждённым.

Необходимо учитывать:

pain severity;

willingness to pay;

implementation complexity;

sales cycle;

competition;

required integrations;

property operational complexity;

decision-maker accessibility;

demonstration value.

Результат должен определить:

FIRST ICP

и

V1 REQUIRED SCOPE.

---

# 29. V1 SCOPE

Status:
DECISION REQUIRED

V1 должен быть:

coherent;

sellable;

operationally useful;

safe;

demonstrable;

implementable.

Но exact V1 scope не должен определяться только из длинного списка Product Bible.

Он зависит от:

FIRST ICP;

Current State;

Gap Analysis;

dependencies;

commercial validation;

implementation cost.

---

# 30. COMMERCIAL VALIDATION

Status:
VALIDATE

Для significant capability использовать цепочку:

FEATURE
→ TARGET CUSTOMER
→ PAIN
→ CURRENT WAY
→ PROPOSED WAY
→ BUSINESS VALUE
→ DEMO VALUE
→ WILLINGNESS TO PAY

Не придумывать:

ROI;

market demand;

pricing;

conversion;

customer savings;

revenue uplift.

Такие claims требуют evidence.

---

# 31. DEMO BACKLOG PRINCIPLE

Status:
APPROVED CONCEPT

Сильная product demonstration должна показывать end-to-end operational flow, а не набор disconnected screens.

Potential future demo flows:

Booking Request
→ Availability
→ Calculation
→ Human Confirmation
→ Reservation

Guest QR
→ Request
→ Task
→ Staff
→ Status
→ Completion

Guest
→ Restaurant Order
→ Kitchen
→ Ready
→ Delivery
→ Charge/Payment where applicable

AI Manager
→ Natural Language Request
→ Verified Context
→ Controlled Tool
→ Result

Конкретные demo flows выбираются после определения V1/ICP.

---

# 32. BACKLOG ENTRY FORMAT

Каждая значимая backlog item должна по возможности содержать:

ID:

TITLE:

STATUS:

PRIORITY:

AREA:

PROBLEM:

BUSINESS VALUE:

CURRENT STATE:

TARGET STATE:

DEPENDENCIES:

RISKS:

IMPLEMENTATION SCOPE:

OUT OF SCOPE:

TESTS:

VERIFIED CRITERIA:

EVIDENCE REQUIRED:

DECISIONS REQUIRED:

Не заполнять неизвестные поля фантазиями.

---

# 33. IMPLEMENTATION GATE

До начала significant implementation должны быть известны:

WHY

WHAT

BUSINESS RULE

CURRENT STATE

TARGET STATE

DEPENDENCIES

RISKS

ACCEPTANCE CRITERIA

VERIFICATION METHOD

Если критическая информация отсутствует:

BLOCKED

или

DECISION REQUIRED.

---

# 34. VERIFICATION GATE

После implementation:

IMPLEMENTED

не изменяется автоматически на:

VERIFIED.

Для VERIFIED требуется evidence.

Potential evidence:

tests passed;

integration tests;

permission tests;

negative tests;

runtime behavior;

data integrity checks;

security checks;

manual acceptance where required.

Конкретный evidence зависит от capability.

---

# 35. KNOWLEDGE UPDATE AFTER IMPLEMENTATION

После успешной реализации:

IMPLEMENT
→ TEST
→ EVIDENCE
→ VERIFIED
→ UPDATE 04_CURRENT_STATE.md

Если реализация изменила утверждённую architecture или Business Rules:

сначала проверить, было ли это явным approved decision.

Нельзя менять canonical target задним числом только потому, что implementation получилась другой.

---

# 36. PRODUCT BIBLE CHANGE RULE

00_PRODUCT_BIBLE.md является frozen product baseline до явного решения об изменении.

Новая идея:

NEW IDEA
→ PROPOSED / VALIDATE
→ ANALYSIS
→ DECISION
→ APPROVED / REJECTED

Только APPROVED изменение может попасть в новую версию Product Bible.

Не изменять Product Bible, чтобы скрыть GAP.

---

# 37. BUSINESS RULE CHANGE RULE

Новая Domain Business Rule:

QUESTION
→ ANALYSIS
→ OPTIONS
→ PROPOSED
→ EXPLICIT DECISION
→ APPROVED / REJECTED
→ UPDATE 01_DOMAIN_BUSINESS_RULES.md

Industry practice не является автоматическим основанием для APPROVED.

---

# 38. ARCHITECTURE CHANGE RULE

Significant Architecture Decision:

PROBLEM
→ REQUIREMENTS
→ CONSTRAINTS
→ OPTIONS
→ TRADE-OFFS
→ RECOMMENDATION
→ DECISION
→ UPDATE 02_SYSTEM_ARCHITECTURE.md IF CANONICAL

Implementation convenience не является достаточным основанием для изменения Product Business Rule.

---

# 39. AI CHANGE RULE

New AI capability:

BUSINESS NEED
→ APPROVED BUSINESS RULE
→ RISK ANALYSIS
→ TOOL DESIGN
→ PERMISSION DESIGN
→ HUMAN CONFIRMATION RULE
→ IMPLEMENTATION
→ TEST
→ EVIDENCE
→ VERIFIED
→ ENABLEMENT

LLM capability alone does not justify product enablement.

---

# 40. DEFERRED / NOT YET DECIDED

Следующие вещи нельзя считать обязательным V1 только потому, что они присутствуют в vision:

full POS;

full KDS;

advanced Signage;

advanced SPA;

IoT;

locks;

advanced Multi-Property;

large enterprise functionality;

all omnichannel integrations;

all payment scenarios;

advanced automation;

complex revenue management.

Каждая capability должна пройти scope decision.

---

# 41. IMMEDIATE NEXT PHASE

Current Knowledge baseline:

00_PRODUCT_BIBLE.md
= CREATED

01_DOMAIN_BUSINESS_RULES.md
= CREATED

02_SYSTEM_ARCHITECTURE.md
= CREATED

03_AI_ADMIN.md
= CREATED

04_CURRENT_STATE.md
= BLOCKED UNTIL REAL PROJECT EVIDENCE

05_DECISIONS_AND_BACKLOG.md
= CREATED

Следующий meaningful project phase после появления реального проекта:

REAL PROJECT
→ CURRENT STATE AUDIT
→ 04_CURRENT_STATE.md
→ GAP ANALYSIS
→ FIRST P0/P1 DECISION

До появления проекта допустимо продолжать:

Product decisions;

Domain Business Rule decisions;

ICP validation;

V1 scope analysis;

integration research;

payment research;

AI architecture decisions.

Но нельзя выдавать это за Current State.

---

# 42. CANONICAL DEVELOPMENT LOOP

PRODUCT VISION
→ APPROVED PRODUCT BIBLE
→ APPROVED BUSINESS RULES
→ TARGET ARCHITECTURE

PARALLEL:

REAL CODE / SYSTEM
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
→ PLAN
→ HUMAN APPROVAL
→ IMPLEMENT
→ TEST
→ EVIDENCE
→ VERIFIED
→ CURRENT STATE UPDATE
→ NEXT PRIORITY

---

# 43. FINAL BACKLOG PRINCIPLE

DO NOT IMPLEMENT RANDOMLY.

DO NOT TURN EVERY IDEA INTO V1.

DO NOT TURN EVERY GAP INTO P0.

DO NOT INVENT CURRENT STATE.

DO NOT MARK IMPLEMENTED AS VERIFIED WITHOUT EVIDENCE.

DO NOT CHANGE PRODUCT TARGET TO MATCH AN INCOMPLETE IMPLEMENTATION.

DO NOT ALLOW TECHNICAL CONVENIENCE TO SILENTLY REDEFINE BUSINESS RULES.

Every meaningful next step must answer:

WHAT PROBLEM ARE WE SOLVING?

WHY NOW?

WHAT IS ALREADY APPROVED?

WHAT IS CURRENTLY VERIFIED?

WHAT IS THE GAP?

WHAT DECISION IS REQUIRED?

WHAT IS THE PRIORITY?

WHAT WILL COUNT AS VERIFIED?
