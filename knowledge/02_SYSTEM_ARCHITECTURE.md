# 02_SYSTEM_ARCHITECTURE.md

# RESORT OS — SYSTEM ARCHITECTURE

Version: 0.1
Qualifier: CANONICAL TARGET ARCHITECTURE — INITIAL BASELINE
Canonical: YES
Document Type: System Architecture
Depends On:
- 00_PRODUCT_BIBLE.md
- 01_DOMAIN_BUSINESS_RULES.md

---

# 1. DOCUMENT PURPOSE

Этот документ определяет TARGET SYSTEM ARCHITECTURE Resort OS.

Он описывает:

- architecture principles;
- system boundaries;
- domain boundaries;
- data ownership principles;
- security boundaries;
- integration principles;
- AI integration boundaries;
- multi-tenancy principles;
- reliability requirements;
- auditability;
- consistency requirements;
- architectural decision rules.

Этот документ НЕ является описанием фактической текущей реализации.

TARGET ARCHITECTURE ≠ CURRENT ARCHITECTURE.

Фактическое состояние должно определяться только через:

04_CURRENT_STATE.md

на основании evidence реального проекта.

Этот документ НЕ должен выдумывать:

- существующий technology stack;
- database engine;
- programming language;
- framework;
- cloud provider;
- repository structure;
- existing API;
- deployment;
- infrastructure;
- integrations.

Если решение ещё не принято:

UNKNOWN / TO BE DESIGNED / VALIDATE.

---

# 2. ARCHITECTURE OBJECTIVE

Status: APPROVED CONCEPT

Resort OS должен развиваться как единая модульная Hospitality Operating System.

Основные архитектурные принципы:

ONE PLATFORM

ONE CORE

MODULAR ARCHITECTURE

SHARED CANONICAL DOMAIN MODEL

CONFIGURATION-DRIVEN CAPABILITIES

ROLE / PERMISSION AWARE

INTEGRATION-READY

AI-ASSISTED

AUDITABLE

SECURE BY DESIGN

MULTI-PROPERTY READY

Основной принцип:

UNIVERSAL INSIDE
→
SIMPLE OUTSIDE

Внутренняя универсальность не должна приводить к одинаковому перегруженному интерфейсу для всех объектов и ролей.

---

# 3. ARCHITECTURE TRUTH

Status: APPROVED
Priority: CRITICAL

Необходимо всегда различать:

TARGET SYSTEM ARCHITECTURE

и

CURRENT SYSTEM ARCHITECTURE.

Этот документ определяет TARGET.

Он не доказывает наличие соответствующей реализации.

Запрещено делать вывод:

"описано в 02_SYSTEM_ARCHITECTURE.md"
→
"существует в коде".

Для доказательства реализации требуется evidence из реальной системы.

---

# 4. ARCHITECTURAL STYLE

Status: APPROVED CONCEPT

Resort OS должен иметь modular domain-oriented architecture.

Конкретная physical architecture пока не утверждена.

Возможные реализации могут включать:

modular monolith;

distributed services;

hybrid architecture.

Validation: VALIDATE
Design: TO BE DESIGNED

Не выбирать microservices только ради масштабности концепции.

Не выбирать monolith только ради простоты.

Решение должно учитывать:

реальный масштаб;
team size;
operational complexity;
deployment complexity;
transaction boundaries;
domain boundaries;
integration requirements;
reliability;
cost;
maintainability.

Главный принцип:

LOGICAL MODULARITY IS REQUIRED.

PHYSICAL DISTRIBUTION IS A SEPARATE DECISION.

---

# 5. CANONICAL DOMAIN MODEL

Status: APPROVED CONCEPT

Resort OS использует:

SHARED CANONICAL DOMAIN MODEL.

Это означает согласованное понимание ключевых domain concepts между модулями.

Примеры:

Property
Room
Guest
Reservation Request
Reservation
Stay
Service
Task
Charge
Payment
Partner / Agent
Staff
Operation

Shared Canonical Domain Model НЕ означает:

одну database;

одну table structure;

один backend service;

отсутствие bounded contexts.

Physical storage architecture определяется отдельно.

---

# 6. HIGH-LEVEL DOMAIN BOUNDARIES

Status: APPROVED CONCEPT

Целевая архитектура должна учитывать следующие product/domain areas:

PMS / Reservations

Guest / Stay

Inventory / Availability

Pricing

Folio / Finance

Operations / Tasks

Housekeeping

Maintenance

Services / Resources

Partners / Agents

Guest CRM

Guest Portal

Dashboard / Command Center

AI Administrator

Omnichannel

Integrations

Multi-Property

Эти области НЕ означают автоматически:

отдельный microservice на каждый domain;

отдельную database;

отдельный repository.

Physical boundaries должны проектироваться после анализа Business Rules и Current State.

---

# 7. PROPERTY / TENANT BOUNDARY

Status: APPROVED CONCEPT
Priority: CRITICAL

Resort OS должен архитектурно поддерживать безопасное разделение данных между соответствующими organizational/property contexts.

Требуются:

tenant isolation;

property isolation;

permission-aware access;

resource-level authorization.

Конкретная tenant model:

UNKNOWN / TO BE DESIGNED

Не утверждено:

Organization → Property hierarchy;

database-per-tenant;

schema-per-tenant;

shared database with tenant keys;

hybrid model.

Выбор должен быть сделан отдельно.

Критический invariant:

пользователь не должен получать доступ к данным другого tenant/property без явного разрешения.

---

# 8. AUTHENTICATION & AUTHORIZATION

Status: APPROVED CONCEPT
Priority: CRITICAL

Authentication и Authorization должны рассматриваться отдельно.

Authentication отвечает:

WHO ARE YOU?

Authorization отвечает:

WHAT ARE YOU ALLOWED TO DO?

Frontend НЕ является security boundary.

Permissions должны проверяться server-side.

Target security model должен учитывать:

RBAC;

resource-level authorization;

tenant/property context;

least privilege;

role-specific capabilities.

Конкретная RBAC model:

UNKNOWN / TO BE DESIGNED

Конкретный authentication provider/mechanism:

UNKNOWN / TO BE DESIGNED

---

# 9. AI PERMISSION ARCHITECTURE

Status: APPROVED
Priority: CRITICAL

Основной invariant:

AI_PERMISSION <= CURRENT_USER_PERMISSION

AI Administrator не должен получать больше прав, чем пользователь/контекст, от имени которого выполняется действие.

AI не должен иметь произвольный unrestricted direct access к production database.

Целевой execution path:

USER / CUSTOMER
→ AI ADMINISTRATOR
→ REASONING
→ CONTROLLED TOOL / FUNCTION
→ AUTHORIZATION
→ RESORT OS DOMAIN/API LAYER
→ DATA / INTEGRATION

Каждый sensitive tool должен иметь:

explicit purpose;

defined inputs;

defined outputs;

authorization checks;

validation;

auditability;

error handling.

Critical actions должны соблюдать Human-in-the-loop rules.

---

# 10. RESERVATION ARCHITECTURE BOUNDARY

Status: APPROVED

Архитектура обязана сохранять утверждённую business boundary:

RESERVATION REQUEST
→ CHECK / CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

AI, Integration, Automation и API не должны обходить этот lifecycle.

Нельзя создавать hidden technical path, позволяющий AI автоматически подтверждать финальную Reservation в обход Human Confirmation.

Конкретная state machine:

TO BE DEFINED in 01_DOMAIN_BUSINESS_RULES.md

Конкретная implementation:

TO BE DESIGNED.

---

# 11. AVAILABILITY / INVENTORY CONSISTENCY

Status: APPROVED CONCEPT
Priority: CRITICAL

Availability и Inventory должны рассматриваться как consistency-critical domains.

Architecture должна предотвращать неконтролируемые состояния, способные привести к:

double booking;

inventory corruption;

lost updates;

conflicting assignments;

incorrect room availability.

Необходимо учитывать:

concurrency;

transaction boundaries;

locking/coordination;

idempotency;

external synchronization;

failure recovery.

Конкретный algorithm:

UNKNOWN / DEPENDS ON BUSINESS RULES

До утверждения Inventory Business Rules окончательная architecture не определяется.

---

# 12. SPLIT STAY ARCHITECTURE

Capability Status: APPROVED
Implementation: TO BE DESIGNED

Architecture должна позволять реализовать:

Split Stay / Partial Room Move.

Она не должна предполагать, что:

ONE STAY = ONE ROOM FOR ALL DATES

если это делает утверждённую capability невозможной.

Однако конкретная model:

StaySegment;

RoomAssignment;

AssignmentPeriod;

или другая структура

НЕ утверждена.

Она должна проектироваться после утверждения детальных Business Rules.

---

# 13. PRICING ARCHITECTURE

Design: TO BE DESIGNED

Pricing должен быть отделён от LLM reasoning.

Critical pricing calculations должны выполняться deterministic business logic.

AI может:

понимать запрос;

собирать параметры;

вызывать Pricing capability;

объяснять результат.

AI не должен самостоятельно придумывать итоговую цену.

Конкретная Pricing Engine architecture зависит от утверждённых Pricing Business Rules.

---

# 14. FOLIO / FINANCE ARCHITECTURE

Design: TO BE DESIGNED
Priority: CRITICAL WHEN IMPLEMENTED

Financial data требует:

traceability;

authorization;

auditability;

consistent state transitions;

safe correction mechanisms;

idempotency where required.

AI не является финансовым source of truth.

Payment provider не является автоматически source of truth для всего Folio domain.

Конкретная Folio architecture определяется после утверждения Business Rules.

---

# 15. PARTNER / AGENT ARCHITECTURE

Status: APPROVED CONCEPT
Design: TO BE DESIGNED

Architecture должна позволять связывать Partner / Agent context с:

source attribution;

Reservations;

Guests/Stays where applicable;

revenue;

commission history;

settlement history.

Конкретная financial model зависит от Business Rules.

Нельзя hardcode commission assumptions до их утверждения.

---

# 16. OPERATIONS / TASK ARCHITECTURE

Status: APPROVED CONCEPT

Повторяющиеся operational workflows могут использовать reusable Task capabilities.

Potential domains:

Housekeeping;

Maintenance;

Guest Requests;

Internal Operations;

Services.

Однако architecture не должна насильно превращать разные business processes в одну универсальную state machine.

Reusable infrastructure допустима.

Business semantics должны сохраняться.

---

# 17. SERVICE / RESOURCE ARCHITECTURE

Status: APPROVED CONCEPT

Resort OS должен поддерживать расширяемую модель Services/Resources.

Potential consumers:

SPA;

activities;

transfers;

facilities;

equipment;

other services.

Architecture должна позволять добавлять новые service capabilities без необходимости переписывать PMS Core.

Но нельзя предполагать, что все Services имеют одинаковые:

capacity;

duration;

pricing;

availability;

resource requirements.

---

# 18. GUEST PORTAL ARCHITECTURE

Status: APPROVED CONCEPT

Guest Portal является внешней security boundary.

Potential entry:

QR
→ SECURE CONTEXT
→ GUEST PORTAL
→ AUTHORIZED RESORT OS CAPABILITIES

Запрещён принцип безопасности:

/room/{public-room-number}
→ unrestricted guest access

Target architecture должна учитывать:

secure token/context;

Stay binding where appropriate;

expiration;

revocation;

authorization;

privacy;

rate limiting;

session behavior.

Конкретный token/auth mechanism:

TO BE DESIGNED.

---

# 19. OMNICHANNEL ARCHITECTURE

Status: APPROVED CONCEPT

Целевая схема:

EXTERNAL CHANNEL
→ CHANNEL ADAPTER
→ OMNICHANNEL GATEWAY
→ IDENTITY / CONVERSATION CONTEXT
→ AI SALES & CONCIERGE
→ CONTROLLED RESORT OS TOOLS

Potential channels:

WhatsApp — VALIDATE

Instagram — VALIDATE

Telegram — VALIDATE

Web — VALIDATE

Channel-specific logic не должна бесконтрольно проникать в Core Domain Logic.

Adapters должны изолировать внешние protocol/provider differences.

Наличие потенциального Adapter не означает существование integration.

---

# 20. INTEGRATION HUB

Status: APPROVED CONCEPT

Целевой принцип:

RESORT OS
↔
INTEGRATION LAYER / HUB
↔
ADAPTERS
↔
EXTERNAL SYSTEMS

Potential external categories:

OTA;

payments;

messaging;

email;

telephony;

maps;

accounting/fiscal systems;

locks/access;

IoT;

automation;

POS/KDS;

Channel Manager;

other hospitality systems.

Каждая integration должна отдельно проверяться по:

official API;

authentication;

authorization/scopes;

webhooks;

rate limits;

idempotency;

regional availability;

pricing;

partner approval;

data policy;

failure behavior.

Нельзя объявлять integration supported без evidence.

---

# 21. BUILD / INTEGRATE / HYBRID

Status: APPROVED

Для каждой capability architecture должна рассматривать:

BUILD

INTEGRATE

HYBRID

DEFER

Решение должно учитывать:

business value;

differentiation;

complexity;

reliability;

vendor dependency;

data ownership;

cost;

security;

maintenance;

time-to-market.

Integration не должна использоваться для обхода Core Business Rules.

---

# 22. API ARCHITECTURE

Design: TO BE DESIGNED

Resort OS должен предоставлять controlled programmatic interfaces там, где они необходимы для:

frontend;

AI tools;

integrations;

automation;

external systems.

Конкретный API style:

REST;

GraphQL;

RPC;

events;

hybrid

не утверждён.

API должен обеспечивать:

authentication;

authorization;

validation;

tenant/property context;

error handling;

idempotency where required;

auditability;

versioning strategy where required.

Не придумывать endpoints до проектирования соответствующего domain.

---

# 23. EVENT / ASYNC ARCHITECTURE

Status: VALIDATE
Design: TO BE DESIGNED

Некоторые процессы могут требовать asynchronous/event-driven behavior.

Potential examples:

notifications;

integration synchronization;

task creation;

audit events;

external webhooks;

background operations.

Однако event-driven architecture не должна использоваться автоматически для всех процессов.

Critical transactional invariants должны иметь понятную consistency model.

Конкретный:

message broker;

event bus;

queue;

event store

UNKNOWN.

---

# 24. IDEMPOTENCY

Status: APPROVED CONCEPT
Priority: CRITICAL WHERE APPLICABLE

Повторный delivery одного logical operation не должен создавать неконтролируемые duplicate effects.

Особое внимание:

payments;

external webhooks;

AI tool calls;

reservation operations;

orders;

integration retries;

background jobs.

Конкретная idempotency architecture:

TO BE DESIGNED.

---

# 25. AUDIT ARCHITECTURE

Status: APPROVED CONCEPT

Значимые actions должны быть auditable.

Целевой audit context:

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

Potential SOURCE:

USER

AI_ADMIN

API

INTEGRATION

AUTOMATION

SYSTEM

Audit trail не должен зависеть только от frontend.

Конкретное storage/retention architecture:

TO BE DESIGNED.

---

# 26. OBSERVABILITY

Status: APPROVED CONCEPT

Production architecture должна предусматривать достаточную observability для диагностики operational failures.

Potential capabilities:

structured logging;

error tracking;

metrics;

health checks;

tracing where justified;

integration monitoring;

AI tool execution logs;

security events.

Конкретный observability stack:

UNKNOWN.

---

# 27. FAILURE HANDLING

Status: APPROVED CONCEPT

Architecture должна проектироваться с учётом failures.

Potential failures:

database unavailable;

external API unavailable;

payment timeout;

duplicate webhook;

channel outage;

partial integration failure;

AI provider failure;

network interruption;

background job failure.

Core Resort OS не должен становиться полностью неработоспособным только потому, что AI capability временно недоступна.

AI IS AN ENHANCEMENT LAYER.

CORE OPERATIONAL CAPABILITIES MUST REMAIN AVAILABLE WITHOUT AI WHERE PRACTICABLE.

---

# 28. AUTOMATION / WORKFLOW TOOLS

Status: APPROVED CONCEPT

External workflow/automation tools могут использоваться для вспомогательной orchestration.

Potential example:

n8n or equivalent.

Однако critical PMS Business Logic не должна зависеть исключительно от external low-code automation.

Critical invariants должны контролироваться Resort OS Domain/Application Layer.

Automation tools не должны обходить:

permissions;

validation;

audit;

business rules.

Конкретная automation platform:

VALIDATE.

---

# 29. DATA OWNERSHIP

Status: APPROVED CONCEPT

Для каждого significant domain должно быть понятно:

кто является authoritative owner данных;

кто имеет право их изменять;

какие integrations получают копии;

какие данные являются derived;

как разрешаются conflicts.

External systems не должны автоматически считаться authoritative source для всех связанных данных.

SOURCE OF TRUTH определяется per domain.

Global principle for operational Resort OS context:

RESORT OS = PRIMARY OPERATIONAL SOURCE OF TRUTH

если explicit integration architecture не определяет иначе.

---

# 30. DATA HISTORY

Status: APPROVED CONCEPT

Business-critical historical information не должно бесконтрольно уничтожаться при изменении текущего состояния.

Особенно важны:

Reservation changes;

Room assignments;

Stay changes;

financial operations;

Partner settlements;

permissions;

critical configuration;

AI actions;

integration actions.

Конкретная history/versioning model:

TO BE DESIGNED.

---

# 31. MULTI-PROPERTY ARCHITECTURE

Status: APPROVED CONCEPT
Implementation: VALIDATE

Architecture не должна создавать фундаментальный тупик для Multi-Property.

Однако exact Multi-Property implementation пока не утверждена.

Необходимо в будущем определить:

organization/property hierarchy;

shared vs isolated data;

Guest profile sharing;

central permissions;

cross-property operations;

financial isolation;

configuration inheritance;

reporting;

integration ownership.

Не создавать преждевременную enterprise complexity без подтверждённой необходимости.

---

# 32. CONFIGURATION & FEATURE CAPABILITIES

Status: APPROVED CONCEPT

Разные Property не обязаны использовать одинаковый набор modules/capabilities.

Architecture должна поддерживать configuration-driven availability функциональности.

Однако:

feature visibility ≠ authorization.

Скрытый UI элемент не является security mechanism.

Server-side permissions остаются обязательными.

Конкретная feature/configuration model:

TO BE DESIGNED.

---

# 33. SECURITY BASELINE

Status: APPROVED
Priority: CRITICAL

Architecture должна учитывать:

authentication;

authorization;

RBAC;

resource-level authorization;

tenant isolation;

property isolation;

least privilege;

server-side permission enforcement;

secret management;

input validation;

API security;

session security;

rate limiting;

webhook verification;

idempotency;

audit logging;

privacy;

backup/recovery;

secure external integrations.

Security controls должны соответствовать фактическим рискам и deployment environment.

Нельзя считать систему secure без evidence.

---

# 34. PAYMENT ARCHITECTURE

Business Requirement: APPROVED
Implementation: VALIDATE / UNKNOWN

Resort OS должен учитывать practical lawful payment scenarios целевых клиентов и гостей, включая сценарии, связанные с платежами, происходящими из России.

Architecture пока НЕ определяет:

provider;

acquirer;

legal route;

currency;

settlement model;

API;

fees;

regional availability.

Каждая конкретная payment architecture требует отдельного исследования.

Payment integration должна учитывать:

security;

idempotency;

webhook verification;

retry behavior;

refunds;

audit;

reconciliation;

provider failure.

Не хранить raw sensitive payment credentials/data без явной технической и compliance необходимости.

---

# 35. F&B ARCHITECTURE

Status: APPROVED CONCEPT
Strategy: VALIDATE

Potential domains:

Restaurant;

Dining Hall;

Bar;

Tables;

Waiters;

Menu;

Room Service;

Kitchen;

KDS.

Conceptual operational flow:

ORDER
→ KITCHEN / SERVICE
→ PREPARATION
→ READY
→ DELIVERY / SERVICE

Order Status,

Payment Status,

Delivery Status

должны рассматриваться как отдельные concerns.

Конкретная POS/KDS strategy:

BUILD / INTEGRATE / HYBRID / DEFER

Status: VALIDATE

---

# 36. COMMAND CENTER

Status: APPROVED CONCEPT

Command Center является aggregation/read/action experience для авторизованного пользователя.

Potential data:

occupancy;

arrivals/departures;

room readiness;

guest requests;

housekeeping;

maintenance;

services;

F&B;

staff tasks;

alerts;

selected financial/management indicators.

Command Center не должен создавать независимый competing source of truth.

Он должен получать данные из authoritative Resort OS domains.

---

# 37. TECHNOLOGY STACK

Status: UNKNOWN

Не утверждены:

Frontend framework;

Backend language/framework;

Database;

Cache;

Queue;

Search engine;

Cloud provider;

Hosting;

Container platform;

CI/CD;

Monitoring stack;

AI provider;

Vector database;

API gateway;

Authentication provider.

НЕ заполнять эти поля industry defaults.

Решения принимаются после:

Current State Audit;

requirements analysis;

scale assumptions;

team constraints;

cost analysis;

architecture decisions.

---

# 38. CURRENT IMPLEMENTATION

Actual implementation state is not defined by this Target Architecture document.

Canonical Current State:

04_CURRENT_STATE.md

This document must not independently classify actual architecture as IMPLEMENTED, VERIFIED, UNKNOWN, PARTIAL or BROKEN.

TARGET ARCHITECTURE ≠ CURRENT ARCHITECTURE.

# 39. ARCHITECTURE DECISION PROCESS

Significant architecture decision должен проходить:

PROBLEM
→ REQUIREMENTS
→ CONSTRAINTS
→ OPTIONS
→ TRADE-OFFS
→ RECOMMENDATION
→ DECISION
→ ADR / CANONICAL UPDATE
→ IMPLEMENTATION
→ VERIFICATION

Не выбирать технологию сначала, а затем придумывать проблему под неё.

---

# 40. ARCHITECTURE CHANGE CONTROL

Новая архитектурная идея:

NEW IDEA
→ PROPOSED
→ ANALYSIS
→ DECISION

До approval она не является canonical architecture.

Если решение влияет только на конкретную implementation task, оно может храниться в:

05_DECISIONS_AND_BACKLOG.md

Если решение меняет долгосрочную canonical architecture, после approval обновляется этот документ.

---

# 41. ARCHITECTURE VALIDATION

Architecture считается успешной не потому, что она выглядит современно.

Она должна поддерживать:

approved Business Rules;

data integrity;

security;

operational reliability;

maintainability;

integration;

product evolution;

reasonable complexity;

commercial requirements.

Architecture должна решать реальные задачи Resort OS.

---

# 42. OPEN ARCHITECTURE DECISIONS

Требуют будущего решения:

Actual Current Architecture

Target physical architecture

Repository structure

Frontend stack

Backend stack

Database technology

Canonical persistence model

Tenant model

Property hierarchy

Authentication mechanism

RBAC model

API style

Availability consistency mechanism

Transaction strategy

Split Stay implementation model

Pricing architecture

Folio architecture

Payment architecture

Integration Hub implementation

Event/queue strategy

Audit storage

Observability stack

Deployment architecture

Backup/recovery architecture

Multi-Property architecture

Guest Portal authentication

Omnichannel providers

AI provider/tool runtime

POS/KDS strategy

Channel Manager strategy

SPA strategy

Automation platform

Не принимать эти решения без достаточного контекста.

---

# 43. RELATION TO OTHER CANONICAL DOCUMENTS

00_PRODUCT_BIBLE.md
defines WHAT PRODUCT WE WANT.

01_DOMAIN_BUSINESS_RULES.md
defines HOW THE BUSINESS MUST BEHAVE.

02_SYSTEM_ARCHITECTURE.md
defines HOW THE TARGET SYSTEM SHOULD BE STRUCTURED.

03_AI_ADMIN.md
defines HOW AI OPERATES SAFELY INSIDE THAT SYSTEM.

04_CURRENT_STATE.md
defines WHAT ACTUALLY EXISTS.

05_DECISIONS_AND_BACKLOG.md
defines WHAT MUST BE DECIDED OR DONE NEXT.

Нельзя смешивать эти ответственности.

---

# 44. VERSIONING

Current Version:

0.1

Reason:

Core architectural principles and safety boundaries are established.

Detailed architecture remains intentionally unresolved until sufficient Business Rules, Current State evidence and product requirements exist.

Version 1.0 should not be assigned merely because the document is long.

It should represent a sufficiently approved architecture baseline for the selected V1 scope.

---

# FINAL ARCHITECTURE PRINCIPLE

DESIGN FROM APPROVED BUSINESS RULES.

VERIFY AGAINST REALITY.

DO NOT INVENT CURRENT STATE.

DO NOT OVER-ENGINEER UNKNOWN REQUIREMENTS.

DO NOT LET AI BYPASS DOMAIN LOGIC.

DO NOT LET INTEGRATIONS BYPASS SECURITY.

DO NOT CONFUSE LOGICAL MODULARITY WITH MICROservices.

DO NOT CHOOSE TECHNOLOGY BEFORE UNDERSTANDING THE PROBLEM.

The target architecture of Resort OS must remain:

MODULAR

DOMAIN-ORIENTED

SECURE

AUDITABLE

INTEGRATION-READY

AI-CONTROLLED

DATA-CONSISTENT

CONFIGURATION-AWARE

MULTI-PROPERTY READY

and proportionate to the real product requirements.

