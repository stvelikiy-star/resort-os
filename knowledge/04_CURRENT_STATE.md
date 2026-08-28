# RESORT OS — CURRENT STATE

Version: 2.2
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL DOCKER STAGING VERIFIED / SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: factual implementation reality only

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL STAGING VERIFIED != EXTERNAL STAGING VERIFIED != PRODUCTION VERIFIED.**

This document records factual implementation evidence only. It does not redefine Product Bible, Domain Business Rules, target architecture or AI governance.

---

## 1. Audited integration baseline

Repository: `stvelikiy-star/resort-os`.

Integration branch: `integration/site-pms-cms-20260827`.

Open integration PR: `#37 — Unify site, V9 PMS/CRM, analytics, staff and staging through Resort Core`.

Latest fully audited executable/package head before this documentation synchronization:

`7eaf9b56579a35c8623b56b3511bc790441fefa0`.

All 23 pull-request-triggered workflow contours associated with that head completed with conclusion `success`:

- NFC Deferred Scope CI — `33199405346`;
- n8n Workflow JSON CI — `33199405358`;
- Public Site Truth CI — `33199405465`;
- Three Crowns Dependency Security Inspection — `33199405451`;
- Production Migration Baseline CI — `33199405463`;
- Three Crowns AI Administrator CI — `33199405450`;
- Realtime PMS CI — `33199405372`;
- PostgreSQL Backup Restore CI — `33199405368`;
- Payment Idempotency CI — `33199405472`;
- Staff Voice CI — `33199405385`;
- n8n Resort Core Contract CI — `33199405421`;
- Guest Services PMS CI — `33199405441`;
- Automation Contract CI — `33199405496`;
- Data Intake Integrity CI — `33199405348`;
- Control Center Monorepo Contract CI — `33199405367`;
- Unified Inbox CI — `33199405539`;
- AI Sales Draft CI — `33199405543`;
- PMS Chessboard Mutation CI — `33199405473`;
- Telegram Sales CI — `33199405356`;
- Hotel Operations CI — `33199405399`;
- Three Crowns Single Server Production Package CI — `33199405351`;
- Resort Core CI — `33199405433`;
- Three Crowns Full Staging Gate — `33199405342`.

These are repository/CI facts. Pull-request workflows test the PR integration context associated with the head; this evidence does not establish external-host, provider, device or production verification.

Documentation-only commits after this head may move the branch without broadening executable verification. The exact audited executable head above remains the release evidence boundary until a later executable head receives equivalent verification.

---

## 2. Current active architecture

Current operational source-of-truth boundary:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint:
`services/api/app/app_entry.py` -> `app.app_entry:app`.

Current repository surfaces:
- `apps/web` — public Next.js application;
- `apps/admin` — PMS/admin Next.js application;
- `apps/staff` — staff Next.js/PWA;
- `services/api` — FastAPI Resort Core;
- `packages/database` — Prisma/PostgreSQL schema and committed migrations;
- `automation/n8n` — controlled orchestration workflows/runbooks;
- `deploy` — one-server Caddy/Docker package;
- `scripts` — integrity, migration, backup/restore, staging, host and public-truth gates;
- `knowledge` / `docs` — canonical rules and implementation evidence.

Google Sheets, n8n and AI are not parallel reservation/inventory/pricing/payment sources of truth.

NFC remains deferred and absent from active application composition.

---

## 3. CI-local Docker staging

STATUS: **VERIFIED on audited executable head `7eaf9b56579a35c8623b56b3511bc790441fefa0` / associated PR integration context.**

Workflow: `Three Crowns Full Staging Gate`.
Run: `33199405342`.
Conclusion: `success`.

The gate covers isolated PostgreSQL, committed migrations, deterministic seed, database invariants, release/public-truth guards, real web/admin/staff/Core container build/start, staging acceptance, active-route scope and teardown.

The staging gate includes the owner-approved guest-facts guard and the three-migration ledger.

This is **CI-local container staging evidence only**. It is not external HTTPS/WSS staging and not production verification.

---

## 4. Single-server production package

STATUS: **VERIFIED IN CI / NOT EXTERNALLY DEPLOYED.**

Workflow: `Three Crowns Single Server Production Package CI`.
Run: `33199405351`.
Conclusion: `success`.

Approved one-server runtime remains:
- Caddy on public 80/443 edge;
- public Next.js web;
- PMS/Admin Next.js;
- Staff PWA;
- FastAPI Resort Core;
- private PostgreSQL;
- pinned n8n `2.36.2`;
- persistent media/PostgreSQL/n8n state;
- local backup path with off-site copy expected.

This does not prove that the purchased `3korony.com` host supports the topology or that deployment has occurred there.

---

## 5. Dependency / build security

STATUS: **VERIFIED FOR THE AUDITED LOCKED FRONTEND TREE IN CI.**

Declared frontend runtime:
- Next.js `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- patched PostCSS override `8.5.23`.

Workflow: `Three Crowns Dependency Security Inspection`.
Run: `33199405451`.
Conclusion: `success`.

Committed lockfiles remain in web/admin/staff and production Dockerfiles use deterministic installs.

---

## 6. Migration / database truth

STATUS: **VERIFIED IN CLEAN CI AND CI-LOCAL DOCKER STAGING.**

Committed migration chain:
- `0_init` — canonical core baseline and PostgreSQL invariants;
- `1_site_content` — `site_content_documents`;
- `2_guest_service_tasks` — structured reservation-linked guest-service context on `operational_tasks`.

`2_guest_service_tasks` adds nullable legacy-compatible fields:
- `reservationId`;
- `serviceCode`;
- `serviceDate`;
- `serviceTime`;
plus reservation FK, guest-service context/time checks and Prisma-aligned indexes.

Verified current facts:
- clean `prisma migrate deploy` succeeds;
- migration ledger is `0_init,1_site_content,2_guest_service_tasks`;
- `site_content_documents` exists;
- development seed contains 84 room positions / 12 room categories;
- the existing 13 critical production-preflight PostgreSQL constraints remain present;
- guest-service migration columns/checks are asserted by migration/staging CI;
- active room/date overlap remains protected by PostgreSQL exclusion constraint;
- payment/date/amount integrity remains database protected.

Evidence:
- Production Migration Baseline CI `33199405463` — `success`;
- PostgreSQL Backup Restore CI `33199405368` — `success`;
- Full Staging Gate `33199405342` — `success`.

The production database itself has not yet been migrated or proven by this evidence.

---

## 7. Reservation / availability / PMS authority

STATUS: **VERIFIED FOR CURRENT THREE CROWNS V1 FLOW IN CI.**

Canonical active boundary:

`ReservationRequest -> manager/human confirmation -> Reservation`.

Verified rules:
- `ReservationRequest != Reservation`;
- request creation does not itself guarantee a room;
- no authoritative global automatic prepayment percentage exists for current V1;
- manager chooses payment amount/terms/method and records accepted payment fact;
- AI/n8n cannot guarantee a Reservation or confirm payment;
- availability and pricing are server-authoritative Core facts;
- payment status and reservation status are separate concepts.

Evidence:
- Resort Core CI `33199405433` — `success`;
- Payment Idempotency CI `33199405472` — `success`;
- PMS Chessboard Mutation CI `33199405473` — `success`;
- Realtime PMS CI `33199405372` — `success`.

The verified PMS mutation contour includes schedule read, move preview/commit, stale-version rejection, resize, Split Stay, CLEAN check-in protection, relocation/history preservation, conflict rollback, checkout/housekeeping and AuditLog evidence.

---

## 8. PMS V9 / universal chessboard current UI

STATUS: **IMPLEMENTED AND CI-VERIFIED THROUGH PMS/CORE/STAGING CONTOURS.**

Primary daily composition:
- `PMSOperationsCockpitV9`;
- `PMSGuestServicesV9`;
- `PMSBulkGuardV9`;
- `PMSUniversalBoard`;
- shared `PMSControlSnapshotProviderV9`.

Current implemented chessboard capabilities include:
- search by guest/phone/booking/room/category/building context;
- room type/building/floor/room-state/reservation-state filters;
- finance/debt, occupancy and block-type filters;
- quick views: arrivals, departures, in-house, free, debt, attention;
- grouping by building/floor/category;
- compact/comfortable density;
- 7/14/21/31-day windows;
- HTTP polling + PMS WebSocket realtime;
- allowed whole-booking drag/move;
- segment move;
- Split Stay / scissors interaction;
- server preview before commit;
- TECH_BLOCK destination protection;
- checked-in history protection;
- unassigned guaranteed-reservation placement;
- fail-closed finance filters when the finance read model is unavailable/incomplete.

This is the canonical operational chessboard. Review/demo packaging must not become a second scheduling source of truth.

---

## 9. Structured Guest Services

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Current flow:

`Reservation -> OperationalTask(type=GUEST_REQUEST) -> service context -> operational status`.

Controlled hotel service codes:
- `TRANSFER`;
- `MEALS`;
- `PARKING`;
- `SAUNA`;
- `BILLIARDS`;
- `EXCURSIONS`.

Water activities are intentionally not represented as hotel services because current public truth defines them as independent seasonal beach operators. Table tennis is free and is not tracked as a paid/request service contour.

The admin API `/api/v1/admin/guest-services` is OWNER/MANAGER scoped, property isolated, reservation linked, validates active `GUARANTEED`/`CHECKED_IN` reservations, rejects duplicate active same reservation/service/date/time, and dynamically resolves relevant room context from reservation assignments.

Creating a guest service does **not** automatically modify `Reservation.totalKgs` or create a `Payment`. Audit evidence records `financial_effect=NONE_AUTOMATIC`.

Dedicated evidence:
- Guest Services PMS CI `33199405441` — `success`.

The dedicated contour covers clean migration, typecheck/compile, real Reservation creation through the manager-confirmation boundary, service creation/list/status transitions, duplicate rejection, invalid time rejection, property isolation, no automatic finance mutation and AuditLog evidence.

---

## 10. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts include `Guest`, `ReservationRequest`, `Reservation` and segmented `InventoryBlock` room/date assignments.

A distinct persisted canonical `Stay` entity is not implemented. Operational stay state is represented primarily through Reservation lifecycle and segmented inventory assignments.

Therefore canonical `Guest != Reservation != Stay` separation is not yet fully implemented. This is a known target/current GAP, not permission for an unreviewed data-model rewrite.

---

## 11. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing is server-side by room type/date using integer KGS values and sale-state controls.

Current Payment domain/CI covers manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Current finance is operational payment control, not statutory accounting. A complete Folio/Charge/Adjustment/Void/Refund accounting domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 12. Authentication / RBAC / property boundary

STATUS: **VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.**

Current evidence includes Argon2 passwords, hashed session tokens, HttpOnly cookies, expiry/revocation, active-user checks, server-side roles, Property binding and AuditLog authentication evidence.

Current runtime is property-selected by `PROPERTY_CODE`.

Generic organization/tenant hierarchy, cross-property workflows and universal resource-level multi-property permissions are not established.

External HTTPS cookie/CORS behavior remains an external staging gate.

---

## 13. Operations / Staff PWA

STATUS: **VERIFIED IN CI; REAL-DEVICE ACCEPTANCE OPEN.**

`OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Hotel Operations CI `33199405399` completed `success` and covers owner/maid/technician authorization, housekeeping assignment/state transitions/rework/inspection/CLEAN acceptance, TECH_BLOCK protection, assignment history/workload and application build checks.

Staff Voice CI `33199405385` also completed `success`.

Real iPhone/Android/Telegram Mini App acceptance remains open.

---

## 14. CRM / omnichannel / AI

STATUS: **PARTIAL; REPOSITORY CONTOURS VERIFIED / LIVE PROVIDERS NOT VERIFIED.**

Approved channel boundary:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets -> mirror/control surface only.

Internal AI Sales remains manager-review draft assistance only. AI does not auto-send, confirm payment or create guaranteed Reservations.

Public website AI Administrator is implemented and CI-covered. It uses Core facts/availability, is rate limited, fails explicitly when provider configuration is unavailable, and hands sellable booking intent to the existing ReservationRequest flow.

Evidence:
- Three Crowns AI Administrator CI `33199405450` — `success`;
- AI Sales Draft CI `33199405543` — `success`;
- n8n Resort Core Contract CI `33199405421` — `success`;
- n8n Workflow JSON CI `33199405358` — `success`;
- Telegram Sales CI `33199405356` — `success`;
- Unified Inbox CI `33199405539` — `success`.

Real OpenAI production credentials, API Green credentials, actual hotel-number webhook/E2E and external HTTPS provider execution remain **NOT VERIFIED / NOT LIVE**.

---

## 15. Public site / owner-approved guest truth

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

Current public site preserves the approved visual design and adds owner-approved guest facts without creating a second design system.

Current owner-approved facts represented in the site truth contour include:
- transfer one-way per vehicle: Manas -> hotel 6500 KGS sedan / 7500 KGS minivan; Tamchy -> hotel 2500 / 3500; Bishkek city -> hotel 5500 / 6500;
- current food pricing retained from the approved official-source baseline until a later owner update;
- free parking for staying guests, stated current capacity 30–50 vehicles;
- sauna in winter only, 5000 KGS/hour, 4–5 people;
- billiards 500 KGS/hour;
- table tennis free;
- excursions presented with current program/price subject to manager confirmation/update;
- thermal springs within walking distance;
- water activities described only as independent seasonal beach operators, not hotel services;
- hotel rules page based on owner-provided rules;
- base inclusion wording for Wi-Fi, own beach, outdoor pool, umbrellas/loungers, free parking and table tennis; meal inclusion depends on rate/option.

Explicit owner rejection/current truth:
- no gym / тренажёрный зал;
- no sports grounds / sports fields / спортивные площадки.

These rejected amenities must not be restored from legacy-site copy.

The site keeps the request-not-confirmation boundary and current payment truth. It must not publish stale fixed 30% prepayment, first-night automatic prepayment, two-day unpaid hold, unverified online-card acquiring, unverified Elsom or AI-generated payment instructions.

Public Site Truth CI `33199405465` — `success`.
Full Staging `33199405342` includes owner guest-facts enforcement.

The current live legacy `3korony.com` must not be represented as the verified new Resort OS deployment.

---

## 16. Dashboard / analytics / control

STATUS: **IMPLEMENTED + CI-COVERED; NOT PRODUCTION-VERIFIED.**

Current Command Center covers occupancy, arrivals/departures, active requests, waiting communications, manager-recorded payments, room attention/states, operations/tasks and finance controls.

Current Reports/Analytics covers date ranges, occupancy/room nights, ADR, RevPAR, allocated booking value, received payments, active debtors, arrivals/departures, in-house/guaranteed reservations, CRM funnel/channels, room-category performance, reservation channels, operations, daily occupancy dynamics and supported CSV exports.

These are management metrics, not statutory accounting/revenue-recognition truth.

---

## 17. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository, but active application composition excludes NFC routers.

NFC Deferred Scope CI `33199405346` and Full Staging `33199405342` completed `success`.

Reactivation requires explicit owner decision.

---

## 18. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

The production register remains fail-closed until exactly 84 physical room rows and unresolved building/floor/mansard/cottage details are owner-confirmed. Development seed data must not be silently promoted into physical production truth.

---

## 19. Deployment state

### CI-local staging
STATUS: **VERIFIED** on executable head `7eaf9b56579a35c8623b56b3511bc790441fefa0` / associated PR integration context. Run `33199405342` — `success`.

### Single-server deployment package
STATUS: **VERIFIED IN CI.** Run `33199405351` — `success`.

### Purchased `3korony.com` hosting
STATUS: **UNKNOWN / BLOCKED ON HOST ACCESS.**

`scripts/host_preflight.sh` is implemented and non-destructive, but no current evidence proves the purchased host type/capacity/root/Docker/network suitability.

### Legacy rollback backup
STATUS: **BLOCKED / NOT VERIFIED.**

No verified full rollback backup of the exact currently live legacy site exists in accessible project evidence. A public crawl or an old emergency archive is not sufficient proof of a full rollback point.

### External HTTPS/WSS staging
STATUS: **BLOCKED / NOT VERIFIED.**

Real TLS, secure cookies, CORS, WSS, firewall/network behavior, real browser and real-device behavior remain unproven.

### Live AI / messaging providers
STATUS: **BLOCKED / NOT VERIFIED.**

Repository configuration does not prove live credentials/provider delivery.

### Production
STATUS: **NOT PRODUCTION READY / NOT PRODUCTION EXECUTED.**

No CI result alone authorizes DNS cutover.

---

## 20. High-priority gaps / blockers

### P0 production blockers
1. purchased host access/capability + non-destructive preflight;
2. verified full rollback backup for the current legacy site;
3. isolated external HTTPS/WSS staging on the real host/network;
4. external rendered public-truth probe against that staging;
5. owner-confirmed physical 84-room register;
6. real iPhone/Android/Telegram acceptance;
7. real website AI browser/mobile acceptance;
8. real provider/WhatsApp acceptance if those contours are launch-enabled;
9. fresh production backup/clean-restore/preflight/secrets/DNS/rollback evidence immediately before cutover.

### P1 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- complete Folio/Charge financial domain;
- universal internal AI Operations Administrator controlled-tool/risk model.

### DEFER
- NFC / beach wallet for current Three Crowns V1.

---

## 21. Foundations to extend rather than rewrite

Preserve unless later evidence proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and exclusion constraint;
- ReservationRequest -> human manager confirmation;
- server-authoritative PMS preview/commit;
- V9 universal chessboard composition;
- reservation-linked structured guest-service tasks;
- payment idempotency;
- AuditLog pattern;
- property-scoped staff session/RBAC baseline;
- OperationalTask engine;
- n8n without direct DB authority;
- public site using Core availability/pricing/ReservationRequest;
- public AI using Core facts without Reservation/payment authority;
- public truth fail-closed guards;
- Command Center/Reports management surfaces;
- dormant NFC isolation;
- current single-server package unless actual host evidence proves a limitation.

---

## 22. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the purchased `3korony.com` hosting, obtain a verified rollback backup of the current legacy site, and—if the host is suitable—deploy an isolated external HTTPS/WSS staging contour before replacing the apex site. Then run the external rendered public-truth probe and complete browser/device acceptance.**

Why this remains next:
- all 23 PR-triggered workflow contours associated with the latest audited executable head are successful;
- CI-local Docker staging is verified;
- the one-server production package is verified in CI;
- the three-migration chain is clean-deploy verified;
- PMS move/resize/Split Stay/realtime and structured Guest Services are verified in repository CI;
- public owner-approved guest facts are guarded in CI/local staging;
- the highest-risk unknown is now the actual external host/network/TLS/cookie/CORS/WSS/browser/device environment.

OWNER involvement should be limited to real human-only blockers: infrastructure access when unavailable to engineering, physical room-register confirmations, launch secrets/financial or provider approval where required, real-device acceptance and irreversible production cutover approval.

LAST AUDITED EXECUTABLE HEAD: `7eaf9b56579a35c8623b56b3511bc790441fefa0`
LAST AUDITED: 2026-08-29
