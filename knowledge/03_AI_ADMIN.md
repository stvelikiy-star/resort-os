# 03_AI_ADMIN.md

# RESORT OS — AI ADMINISTRATOR

Version: 0.1
Qualifier: CANONICAL AI ARCHITECTURE — INITIAL BASELINE
Canonical: YES
Document Type: AI Administrator Product & Architecture Rules
Depends On:
- 00_PRODUCT_BIBLE.md
- 01_DOMAIN_BUSINESS_RULES.md
- 02_SYSTEM_ARCHITECTURE.md

---

# 1. DOCUMENT PURPOSE

Этот документ определяет каноническую роль AI Administrator внутри Resort OS.

Он фиксирует:

- назначение AI Administrator;
- product boundaries;
- authority boundaries;
- interaction model;
- tool-use principles;
- Human-in-the-loop;
- permission model;
- hallucination prevention;
- operational safety;
- omnichannel principles;
- audit requirements;
- failure behavior;
- verification requirements.

Этот документ НЕ определяет:

- конкретного LLM provider;
- конкретную model;
- конкретный SDK;
- конкретный vector database;
- конкретный agent framework;
- конкретные API endpoints;
- существующую реализацию AI;
- фактические integrations.

Если это не подтверждено:

UNKNOWN / VALIDATE / TO BE DESIGNED.

---

# 2. PRODUCT ROLE

Status: APPROVED

AI Administrator is a central product layer and strategic differentiator of Resort OS.

AI Administrator НЕ является просто:

FAQ chatbot;

text generator;

search box;

support widget;

decorative AI feature.

Целевая роль:

дать пользователю возможность взаимодействовать с Resort OS обычным языком и безопасно выполнять разрешённые operational workflows через controlled Resort OS capabilities.

Основной принцип:

NATURAL LANGUAGE
→ UNDERSTAND INTENT
→ READ REAL CONTEXT
→ USE CONTROLLED TOOLS
→ APPLY BUSINESS RULES
→ RETURN VERIFIED RESULT

---

# 3. TWO PRIMARY AI CONTOURS

Status: APPROVED

AI Administrator имеет два основных product contours.

## 3.1 AI OPERATIONS ADMINISTRATOR

Работает внутри Resort OS для:

owners;

managers;

administrators;

reception;

authorized staff.

Potential capabilities:

read operational context;

answer questions about the property;

find relevant operational information;

assist with reservations;

assist with guests/stays;

assist with tasks;

assist with housekeeping;

assist with maintenance;

assist with services;

assist with management workflows;

prepare actions;

execute explicitly permitted actions through tools.

Конкретные capabilities зависят от:

implemented Resort OS functionality;

current user permissions;

approved AI tools.

---

## 3.2 AI SALES & CONCIERGE

Работает через guest/customer-facing communication channels.

Potential responsibilities:

understand inquiry;

answer verified property questions;

collect booking requirements;

check availability through Resort OS;

request pricing calculation;

create Reservation Request;

answer service questions;

assist existing guests;

route operational requests;

support concierge interactions.

Potential channels:

Web — VALIDATE

Telegram — VALIDATE

WhatsApp — VALIDATE

Instagram — VALIDATE

Другие channels могут добавляться через adapters после validation.

Наличие channel в target architecture НЕ означает существование working integration.

---

# 4. SOURCE OF TRUTH

Status: APPROVED
Priority: CRITICAL

SOURCE OF TRUTH = RESORT OS

AI Administrator не является источником operational truth.

AI не должен придумывать:

availability;

price;

Reservation;

Reservation status;

Guest;

Stay;

Room;

Room status;

Payment;

Payment status;

Folio;

Order;

Order status;

Task;

Task status;

Service availability;

Partner financial data;

operational metrics.

Если ответ зависит от актуальных данных Resort OS:

AI должен получить эти данные через разрешённый system capability/tool.

Если данные недоступны:

AI должен явно сообщить, что информация не подтверждена.

UNKNOWN ≠ PERMISSION TO GUESS.

---

# 5. CORE EXECUTION ARCHITECTURE

Status: APPROVED CONCEPT

Целевой execution flow:

USER / CUSTOMER
↓
AI ADMINISTRATOR
↓
INTENT & CONTEXT UNDERSTANDING
↓
POLICY / PERMISSION / BUSINESS RULE CHECK
↓
CONTROLLED TOOL / FUNCTION
↓
RESORT OS APPLICATION / DOMAIN LAYER
↓
DATA / INTEGRATIONS
↓
VERIFIED RESULT
↓
AI RESPONSE

AI не должен использовать arbitrary unrestricted production database access как основной execution mechanism.

AI actions должны проходить через controlled capabilities.

---

# 6. PERMISSION INVARIANT

Status: APPROVED
Priority: CRITICAL

AI_PERMISSION <= CURRENT_USER_PERMISSION

AI никогда не получает больше authority, чем разрешено текущему user/context.

Если пользователь не имеет права:

просматривать данные;

изменять данные;

создавать resource;

выполнять operation;

AI также не должен иметь это право от его имени.

Prompt instruction НЕ является security boundary.

Authorization должен обеспечиваться системой.

---

# 7. TOOL-FIRST OPERATIONAL MODEL

Status: APPROVED

Для factual operational actions AI должен использовать controlled tools/functions.

Каждый significant tool должен иметь:

clear purpose;

defined inputs;

defined outputs;

authorization;

input validation;

business-rule validation;

tenant/property context;

error handling;

auditability.

Potential conceptual tools:

get_availability

calculate_price

create_reservation_request

get_reservation

get_guest

get_stay

get_room_status

create_guest_request

create_task

get_task_status

get_service_availability

get_property_information

Конкретные названия, schemas и APIs:

TO BE DESIGNED.

Эти примеры НЕ являются утверждёнными endpoints.

---

# 8. READ VS WRITE ACTIONS

Status: APPROVED CONCEPT

AI capabilities должны различать:

READ ACTIONS

и

WRITE / MUTATING ACTIONS.

READ actions могут быть менее рискованными, но всё равно требуют authorization.

WRITE actions требуют:

permission check;

business-rule validation;

input validation;

audit;

clear result.

Critical write actions могут дополнительно требовать:

Human Confirmation.

---

# 9. RESERVATION SAFETY

Status: APPROVED
Priority: CRITICAL

AI может:

понять booking request;

собрать параметры;

проверить availability через Resort OS;

получить расчёт через deterministic Pricing capability;

объяснить доступные варианты;

создать Reservation Request;

передать Request человеку.

AI НЕ может самостоятельно выполнить:

RESERVATION REQUEST
→ CONFIRMED RESERVATION

Утверждённый lifecycle:

RESERVATION REQUEST
→ CHECK / CALCULATION
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

Human Confirmation является обязательной boundary.

AI не должен обходить её:

через tool;

через integration;

через automation;

через direct database access;

через hidden workflow.

---

# 10. PRICING SAFETY

Status: APPROVED

AI не рассчитывает critical final price посредством свободного LLM reasoning.

AI может:

извлечь параметры из natural language;

запросить Pricing capability;

получить structured result;

объяснить результат пользователю.

Итоговые business calculations должны происходить через deterministic Resort OS logic.

Если Pricing capability не может подтвердить цену:

AI не должен придумывать её.

---

# 11. AVAILABILITY SAFETY

Status: APPROVED

AI не определяет availability на основании предположений или conversation memory.

Availability должна поступать из authoritative Resort OS capability.

AI должен учитывать, что availability может изменяться.

Полученный ранее результат не должен автоматически считаться актуальным бесконечно.

Точная freshness policy:

TO BE DESIGNED.

---

# 12. HUMAN-IN-THE-LOOP

Status: APPROVED CONCEPT

Human-in-the-loop используется для critical actions в соответствии с Business Rules.

Уже утверждено:

FINAL RESERVATION CONFIRMATION
=
HUMAN CONFIRMATION REQUIRED

Другие critical/financial actions:

DECISION REQUIRED.

Potential examples, НЕ являющиеся автоматически утверждёнными:

refund;

large financial adjustment;

reservation cancellation;

folio correction;

permission change;

critical configuration change.

Для каждого такого action должен быть отдельно определён approval policy.

---

# 13. CONFIRMATION DESIGN

Status: APPROVED CONCEPT

Когда action требует Human Confirmation, AI должен:

1. Подготовить действие.
2. Показать человеку существенные параметры.
3. Не представлять действие как выполненное.
4. Получить требуемое confirmation.
5. Только после этого вызвать разрешённый execution capability.
6. Получить фактический result.
7. Сообщить фактический outcome.

AI не должен считать фразы вроде:

"я подготовил"

равнозначными:

"операция выполнена".

---

# 14. ACTION RESULT TRUTH

Status: APPROVED
Priority: CRITICAL

AI должен различать:

INTENT

REQUEST

ATTEMPT

SUCCESS

FAILURE

UNKNOWN RESULT

Если tool call завершился ошибкой:

AI не должен говорить, что действие выполнено.

Если result неизвестен:

status = UNKNOWN RESULT.

Если операция была только подготовлена:

status = NOT EXECUTED / AWAITING CONFIRMATION.

Нельзя превращать optimistic language в ложное подтверждение действия.

---

# 15. HALLUCINATION GUARDRAIL

Status: APPROVED
Priority: CRITICAL

AI запрещено выдумывать факты о Resort OS.

Особенно:

availability;

prices;

bookings;

payments;

room state;

guest data;

stay data;

tasks;

orders;

services;

integrations;

system capabilities.

Если нужный tool отсутствует:

AI должен сказать, что operation недоступна через текущие capabilities.

Если данных недостаточно:

AI должен запросить недостающие данные или обозначить UNKNOWN.

---

# 16. PRODUCT CAPABILITY TRUTH

Status: APPROVED

AI не должен утверждать пользователю, что Resort OS умеет функцию только потому, что она:

описана в Product Bible;

запланирована;

предложена;

есть в backlog;

присутствует в target architecture.

Для operational claim требуется соответствующая Current State evidence.

PLANNED ≠ IMPLEMENTED

IMPLEMENTED ≠ VERIFIED

TARGET ≠ CURRENT

---

# 17. CONTEXTUAL AI

Status: APPROVED CONCEPT

AI Administrator должен быть context-aware внутри Resort OS.

Potential contexts:

Dashboard;

Reservation;

Guest;

Stay;

Room;

Task;

Housekeeping;

Maintenance;

Service;

Partner;

Command Center.

Например:

если пользователь находится в Reservation context, AI может получить authorized reservation context без необходимости заставлять пользователя повторять каждый identifier.

Однако UI context НЕ заменяет authorization.

---

# 18. CONVERSATION CONTEXT

Status: APPROVED CONCEPT

Conversation context может помогать понимать:

references;

follow-up questions;

current workflow;

user intent.

Но conversation memory не является authoritative operational database.

Если пользователь говорит:

"эта бронь"

AI должен определить фактический Reservation context через system context/tool.

Не использовать LLM memory как замену system lookup для critical data.

---

# 19. IDENTITY CONTEXT

Design: TO BE DESIGNED

Для каждого AI interaction необходимо понимать:

кто пользователь;

какой tenant;

какой property;

какая role;

какие permissions;

какой current context.

Для guest-facing AI дополнительно может требоваться:

guest identity;

Stay context;

secure guest session.

Конкретная identity architecture определяется в System Architecture.

---

# 20. GUEST-FACING AI SAFETY

Status: APPROVED CONCEPT

Guest-facing AI должен иметь более ограниченную authority, чем internal staff AI.

Guest не должен получать:

staff-only information;

other guest information;

internal financial data;

private operational data;

unauthorized property data.

Guest-facing AI должен работать только в разрешённом guest context.

GUEST A
≠
GUEST B

STAY A
≠
STAY B

unless explicitly authorized.

---

# 21. OMNICHANNEL MODEL

Status: APPROVED CONCEPT

Target flow:

EXTERNAL CHANNEL
→ CHANNEL ADAPTER
→ OMNICHANNEL GATEWAY
→ IDENTITY / CONVERSATION CONTEXT
→ AI SALES & CONCIERGE
→ CONTROLLED RESORT OS TOOLS

Channel-specific behavior должен быть изолирован через adapters.

Core AI business logic не должен зависеть напрямую от одного messenger/provider.

Каждый channel требует отдельной validation:

official API;

authentication;

permissions;

message capabilities;

webhooks;

rate limits;

pricing;

regional availability;

policy restrictions.

---

# 22. CHANNEL IDENTITY

Status: VALIDATE

External channel identity НЕ должна автоматически считаться Guest identity.

Например:

messenger account
≠ automatically verified Guest/Stay.

Может потребоваться identity linking/verification.

Точные rules:

TO BE DESIGNED.

---

# 23. AI OPERATIONS ADMINISTRATOR — READ CAPABILITIES

Status: APPROVED CONCEPT

AI Operations Administrator может потенциально отвечать на вопросы типа:

какие заезды сегодня;

какие выезды сегодня;

какие номера не готовы;

какие requests открыты;

какие maintenance issues существуют;

какие задачи просрочены;

какая Reservation информация доступна;

какой Guest/Stay context доступен.

Но ответ допустим только если:

capability реализована;

данные доступны;

user authorized;

result получен из authoritative source.

---

# 24. AI OPERATIONS ADMINISTRATOR — ACTION CAPABILITIES

Status: APPROVED CONCEPT

Potential actions:

create Reservation Request;

create Task;

create Guest Request;

prepare operational action;

update permitted non-critical data;

route request;

assist staff workflow.

Каждый action должен быть отдельно реализован как controlled capability.

AI не получает generic:

execute_anything()

или unrestricted:

run_sql()

как production business interface.

---

# 25. AI SALES & CONCIERGE — BOOKING FLOW

Status: APPROVED CONCEPT

Potential target flow:

CUSTOMER
→ BOOKING INTENT
→ REQUIRED PARAMETERS
→ AVAILABILITY CHECK
→ PRICE CALCULATION
→ OPTIONS
→ CUSTOMER INTEREST
→ RESERVATION REQUEST
→ HUMAN CONFIRMATION
→ CONFIRMED RESERVATION

AI должен ясно различать:

availability information;

price quote;

Reservation Request;

Confirmed Reservation.

---

# 26. AI SALES & CONCIERGE — SERVICE FLOW

Status: APPROVED CONCEPT

Potential guest flow:

GUEST
→ NATURAL LANGUAGE REQUEST
→ INTENT
→ VERIFIED SERVICE/CAPABILITY
→ AUTHORIZED ACTION
→ OPERATIONAL REQUEST
→ STATUS
→ RESULT

AI не должен обещать service, которого нет в Property configuration/current verified capability.

---

# 27. SPECIALIZED AI COMPETENCIES

Status: APPROVED CONCEPT

Внутри AI architecture могут существовать specialized competencies.

Potential examples:

Reservation competence;

Operations competence;

Guest Service competence;

Maintenance competence;

F&B competence;

Analytics competence.

Но пользователь не обязан взаимодействовать с множеством отдельных bots.

Product principle:

ONE AI ADMINISTRATOR EXPERIENCE

может использовать internal specialization.

Конкретная multi-agent architecture:

VALIDATE / TO BE DESIGNED.

Не использовать multi-agent architecture без доказанной необходимости.

---

# 28. LLM VS DETERMINISTIC LOGIC

Status: APPROVED
Priority: CRITICAL

LLM подходит для:

natural language understanding;

intent extraction;

conversation;

summarization;

explanation;

tool selection;

assistance;

unstructured information processing.

Deterministic logic должна использоваться для:

critical business rules;

authorization;

pricing calculations;

inventory consistency;

financial calculations;

state transitions;

validation;

idempotency;

security controls.

LLM не должен заменять deterministic domain logic там, где ошибка может нарушить business integrity.

---

# 29. STRUCTURED TOOL INPUT

Status: APPROVED CONCEPT

Перед выполнением significant tool action AI должен преобразовать natural language intent в structured validated parameters.

Пример conceptual transformation:

"Нужен двухместный номер с 10 по 13 сентября"

→

check_in
check_out
occupancy
requested accommodation criteria

Конкретная schema определяется tool contract.

Missing required parameters должны быть собраны до execution.

---

# 30. AMBIGUITY HANDLING

Status: APPROVED

Если запрос допускает несколько materially different interpretations и неправильный выбор может привести к ошибочному действию:

AI должен уточнить intent.

Для low-risk read-only queries AI может использовать разумный context, если ambiguity не влияет существенно на результат.

Для critical/mutating actions:

DO NOT GUESS MATERIAL PARAMETERS.

---

# 31. AI AUDITABILITY

Status: APPROVED
Priority: CRITICAL

Meaningful AI actions должны быть auditable.

Target audit context:

WHO

WHEN

TENANT

PROPERTY

AI CONTEXT

ACTION

TOOL

RESOURCE

INPUT / MATERIAL PARAMETERS

RESULT

SOURCE

CONFIRMATION WHEN REQUIRED

ERROR WHEN APPLICABLE

Не обязательно сохранять unrestricted hidden reasoning.

Audit должен фиксировать operationally relevant facts.

---

# 32. PROMPT INJECTION / UNTRUSTED DATA

Status: APPROVED CONCEPT
Priority: CRITICAL

External content может быть untrusted.

Potential sources:

guest messages;

external channel messages;

uploaded content;

integration payloads;

web content;

property-entered content.

Untrusted content не должно иметь authority изменять:

system instructions;

permissions;

business rules;

tool authorization;

security policies.

Data must remain data.

Instructions from untrusted content must not automatically become system authority.

---

# 33. TOOL OUTPUT TRUST

Status: APPROVED CONCEPT

Tool output должен интерпретироваться согласно его source and contract.

AI не должен считать любой arbitrary external text authoritative.

Для critical actions authoritative data source должен быть определён architecture/business rules.

Malformed, incomplete или contradictory tool results должны приводить к:

error handling;

UNKNOWN;

re-check;

human escalation

в зависимости от context.

---

# 34. ERROR HANDLING

Status: APPROVED

Если tool/system operation fails, AI должен:

1. Не объявлять success.
2. Сохранить distinction между requested и completed.
3. Сообщить понятный result.
4. Не придумывать missing output.
5. Предложить допустимый next step, если он известен.

Пример status logic:

TOOL SUCCESS
→ report verified success.

TOOL FAILURE
→ report failure.

TOOL TIMEOUT / UNCERTAIN
→ report unknown outcome and require verification/retry according to safe policy.

---

# 35. RETRIES & IDEMPOTENCY

Status: APPROVED CONCEPT

AI-driven mutating operations должны учитывать idempotency.

AI не должен бесконтрольно повторять action после timeout/error, если повтор может создать duplicate effect.

Особенно:

Reservation Requests;

payments;

orders;

tasks;

external integrations.

Retry policy определяется соответствующим tool/system contract.

---

# 36. FINANCIAL ACTIONS

Status: APPROVED CONCEPT
Details: DECISION REQUIRED

AI может помогать с financial context только в пределах разрешённых capabilities.

AI не должен:

придумывать payment status;

придумывать refund result;

выдумывать balance;

изменять financial records без разрешённого controlled action.

Точный список financial operations, доступных AI:

DECISION REQUIRED.

Human-in-the-loop policy:

DECISION REQUIRED per action.

---

# 37. PARTNER / AGENT AI

Status: APPROVED CONCEPT

AI может потенциально помогать с:

Partner lookup;

Reservation attribution;

commission information;

settlement history;

related operational questions.

Но financial values должны поступать из Resort OS.

AI не должен самостоятельно вычислять commission по неутверждённой формуле.

---

# 38. COMMAND CENTER AI

Status: APPROVED CONCEPT

AI может быть natural-language layer над Command Center.

Potential questions:

"Что сейчас требует внимания?"

"Какие номера ещё не готовы?"

"Какие гостевые запросы открыты?"

"Какие проблемы критичны?"

Ответ должен формироваться из verified operational data.

AI может:

summarize;

prioritize according to approved rules;

explain;

navigate;

prepare actions.

Но не должен придумывать operational events.

---

# 39. AI WITHOUT CORE SYSTEM

Status: APPROVED

AI Administrator не должен быть единственным способом управлять Resort OS.

Core UI/API должны обеспечивать основные operational capabilities без обязательной зависимости от LLM.

Если AI provider недоступен:

Core Resort OS должен продолжать выполнять critical non-AI operations where technically practicable.

AI FAILURE ≠ TOTAL PMS FAILURE.

---

# 40. MODEL / PROVIDER STRATEGY

Status: VALIDATE

Конкретный:

LLM provider;

model;

fallback model;

embedding model;

agent framework;

tool runtime;

vector storage

не утверждены.

Выбор должен учитывать:

capability;

reliability;

tool use;

structured outputs;

latency;

cost;

privacy;

regional availability;

security;

vendor dependency.

Не hardcode architecture вокруг model name без необходимости.

---

# 41. KNOWLEDGE / RETRIEVAL

Status: APPROVED CONCEPT
Design: TO BE DESIGNED

AI может использовать knowledge/retrieval для:

property information;

policies;

service descriptions;

internal documentation;

approved operational knowledge.

Но retrieval knowledge не заменяет live operational data.

Пример:

Knowledge может сообщить:

"Завтрак проходит с 07:00 до 10:00"

если это актуальная approved property information.

Но вопрос:

"Номер 305 сейчас свободен?"

должен проверяться через live Resort OS capability.

STATIC KNOWLEDGE ≠ LIVE OPERATIONAL STATE.

---

# 42. DATA PRIVACY

Status: APPROVED CONCEPT
Priority: CRITICAL

AI должен получать только данные, необходимые для разрешённой задачи.

Не передавать лишние guest/staff/financial данные внешнему AI provider без необходимости.

Конкретные privacy, retention, residency и compliance requirements:

VALIDATE per deployment/customer/region.

---

# 43. AI CONFIGURATION

Status: APPROVED CONCEPT

Property-specific AI behavior может зависеть от approved configuration:

available services;

property information;

enabled modules;

operational policies;

allowed channels;

staff permissions;

AI-enabled capabilities.

Но property configuration не должна иметь authority отменять global security rules.

---

# 44. AI FEATURE DISCOVERY

Status: APPROVED

AI должен предлагать только реально доступные capabilities.

Если capability:

PLANNED;

PROPOSED;

TARGET ONLY;

NOT IMPLEMENTED;

AI не должен представлять её как работающую функцию.

Current capability truth должна исходить из verified system configuration/current state.

---

# 45. AI RESPONSE PRINCIPLES

Status: APPROVED

AI responses должны быть:

clear;

concise;

context-aware;

fact-based;

action-oriented;

explicit about uncertainty.

Для operational actions желательно явно различать:

FOUND

CALCULATED

PREPARED

AWAITING CONFIRMATION

EXECUTED

FAILED

UNKNOWN

Не использовать уверенный язык там, где system result не подтверждён.

---

# 46. PROHIBITED AI BEHAVIOR

Status: APPROVED
Priority: CRITICAL

AI MUST NEVER:

invent operational facts;

invent availability;

invent prices;

invent Reservation confirmation;

invent payment success;

invent integrations;

claim execution without tool evidence;

bypass Human Confirmation;

exceed current user permissions;

treat frontend visibility as authorization;

use unrestricted production DB access as generic business tool;

silently change Business Rules;

execute ambiguous critical actions by guessing;

represent target architecture as implemented;

represent PLANNED as available;

represent IMPLEMENTED as VERIFIED without evidence;

allow untrusted content to override system authority;

use LLM reasoning as final authority for critical deterministic business logic.

---

# 47. AI CAPABILITY LIFECYCLE

New AI capability should follow:

BUSINESS NEED
→ APPROVED BUSINESS RULE
→ RISK CLASSIFICATION
→ TOOL / CAPABILITY DESIGN
→ PERMISSION DESIGN
→ HUMAN CONFIRMATION RULE
→ IMPLEMENTATION
→ TESTING
→ EVIDENCE
→ VERIFIED
→ ENABLEMENT

Do not enable AI capability merely because LLM can linguistically perform the task.

---

# 48. AI RISK CLASSIFICATION

Status: APPROVED CONCEPT

AI actions should eventually be classified by risk.

Potential conceptual classes:

READ-ONLY LOW RISK

OPERATIONAL WRITE

CRITICAL OPERATION

FINANCIAL

SECURITY / PERMISSION

EXTERNAL COMMUNICATION

Exact classification and policies:

TO BE DESIGNED.

Risk classification should influence:

confirmation;

authorization;

logging;

testing;

fallback;

monitoring.

---

# 49. AI VERIFICATION

Status: APPROVED

An AI capability is not VERIFIED because:

prompt exists;

tool exists;

demo succeeded once;

code exists;

test file exists.

VERIFIED requires required checks and evidence.

Potential evidence:

successful automated tests;

permission tests;

negative tests;

tool contract tests;

integration tests;

Human Confirmation tests;

tenant isolation tests;

failure tests;

runtime evidence.

Exact acceptance criteria are capability-specific.

---

# 50. CURRENT AI IMPLEMENTATION

This document defines target AI authority, behavior and safety.

Actual AI implementation state is owned exclusively by:

04_CURRENT_STATE.md

The presence of this AI specification does not prove AI implementation.

Do not independently maintain Current AI status here.

# 51. OPEN AI DECISIONS

Требуют будущего решения/validation:

LLM provider;

model strategy;

fallback strategy;

tool runtime;

agent architecture;

single-agent vs internal multi-agent;

conversation storage;

memory strategy;

retrieval architecture;

property knowledge architecture;

prompt versioning;

AI observability;

AI evaluation framework;

risk classification;

Human Confirmation matrix;

financial action policy;

guest identity verification;

channel identity linking;

WhatsApp integration;

Instagram integration;

Telegram integration;

Web chat architecture;

privacy requirements;

data retention;

regional restrictions;

cost controls;

rate limits;

fallback behavior;

AI SLA requirements.

Не заполнять эти решения предположениями.

---

# 52. RELATION TO OTHER KNOWLEDGE FILES

00_PRODUCT_BIBLE.md

определяет продукт и место AI Administrator в Resort OS.

01_DOMAIN_BUSINESS_RULES.md

определяет Business Rules, которые AI обязан соблюдать.

02_SYSTEM_ARCHITECTURE.md

определяет system/security/integration boundaries.

03_AI_ADMIN.md

определяет AI-specific authority, behavior and architecture.

04_CURRENT_STATE.md

должен доказать, что реально реализовано.

05_DECISIONS_AND_BACKLOG.md

хранит pending/approved decisions и дальнейшие задачи.

---

# 53. CHANGE CONTROL

Новая AI idea:

NEW IDEA
→ PROPOSED
→ BUSINESS VALUE
→ RISK ANALYSIS
→ ARCHITECTURE ANALYSIS
→ DECISION
→ APPROVED / REJECTED / VALIDATE
→ IMPLEMENTATION
→ VERIFICATION

Не добавлять AI capability в canonical truth только потому, что она технически возможна.

---

# FINAL AI PRINCIPLE

AI ADMINISTRATOR IS A CONTROLLED INTELLIGENCE LAYER OVER RESORT OS.

AI MUST UNDERSTAND NATURAL LANGUAGE.

AI MUST USE REAL SYSTEM DATA.

AI MUST RESPECT BUSINESS RULES.

AI MUST RESPECT USER PERMISSIONS.

AI MUST USE CONTROLLED TOOLS.

AI MUST REQUIRE HUMAN CONFIRMATION WHERE REQUIRED.

AI MUST NEVER INVENT OPERATIONAL TRUTH.

AI MUST NEVER CLAIM AN ACTION SUCCEEDED WITHOUT EVIDENCE.

AI MUST NEVER BECOME THE SECURITY BOUNDARY.

AI MUST NEVER REPLACE DETERMINISTIC CRITICAL BUSINESS LOGIC.

The desired experience is:

ASK NATURALLY
→ UNDERSTAND CONTEXT
→ VERIFY DATA
→ APPLY PERMISSIONS
→ USE SAFE TOOL
→ CONFIRM WHEN REQUIRED
→ EXECUTE
→ VERIFY RESULT
→ REPORT TRUTH
