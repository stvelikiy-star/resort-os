# RESORT OS — CURRENT STATE

Version: 2.3
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

`c9861d4276e7733b9d4e724cf0a7ad4fa2cc3aeb`.

All 24 pull-request-triggered workflow contours associated with that executable head completed with conclusion `success`:

- Public Site Truth CI — `33242397291`;
- n8n Workflow JSON CI — `33242397213`;
- NFC Deferred Scope CI — `33242397292`;
- Three Crowns Dependency Security Inspection — `33242397265`;
- Production Migration Baseline CI — `33242397303`;
- Three Crowns AI Administrator CI — `33242397185`;
- Payment Idempotency CI — `33242397343`;
- Staff Voice CI — `33242397233`;
- n8n Resort Core Contract CI — `33242397245`;
- Automation Contract CI — `33242397271`;
- Realtime PMS CI — `33242397229`;
- Data Intake Integrity CI — `33242397308`;
- PostgreSQL Backup Restore CI — `33242397193`;
- Guest Services PMS CI — `33242397241`;
- Owner Intelligence CI — `33242397195`;
- Telegram Sales CI — `33242397322`;
- AI Sales Draft CI — `33242397236`;
- PMS Chessboard Mutation CI — `33242397316`;
- Hotel Operations CI — `33242397264`;
- Control Center Monorepo Contract CI — `33242397216`;
- Three Crowns Single Server Production Package CI — `33242397260`;
- Three Crowns Full Staging Gate — `33242397283`;
- Resort Core CI — `33242397270`;
- Unified Inbox CI — `33242397317`.

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
- `scripts` — integrity, migration, backup/restore, staging, host, public-truth and owner-intelligence gates;
- `knowledge` / `docs` — canonical rules and implementation evidence.

Google Sheets, n8n and AI are not parallel reservation/inventory/pricing/payment sources of truth.

NFC remains deferred and absent from active application composition.

---

## 3. CI-local Docker staging

STATUS: **VERIFIED on audited executable head `c9861d4276e7733b9d4e724cf0a7ad4fa2cc3aeb` / associated PR integration context.**

Workflow: `Three Crowns Full Staging Gate`.
Run: `33242397283`.
Conclusion: `success`.

The gate covers isolated PostgreSQL, committed migrations, deterministic seed, database invariants, release/public-truth guards, real web/admin/staff/Core container build/start, staging acceptance, active-route scope and teardown.

This is **CI-local container staging evidence only**. It is not external HTTPS/WSS staging and not production verification.

---

## 4. Single-server production package

STATUS: **VERIFIED IN CI / NOT EXTERNALLY DEPLOYED.**

Workflow: `Three Crowns Single Server Production Package CI`.
Run: `33242397260`.
Conclusion: `success`.

Current one-server runtime package remains:
- Caddy on public 80/443 edge;
- public Next.js web;
- PMS/Admin Next.js;
- Staff PWA;
- FastAPI Resort Core;
- PostgreSQL for the current package;
- pinned n8n `2.36.2`;
- persistent media/PostgreSQL/n8n state;
- backup tooling and off-site-copy expectation.

Owner-approved production direction may use Beget VPS plus managed PostgreSQL DBaaS and S3 for stronger operational autonomy. That direction is **approved architecture/planning, not externally implemented or verified current production state**.

---

## 5. Dependency / build security

STATUS: **VERIFIED FOR THE AUDITED LOCKED FRONTEND TREE IN CI.**

Declared frontend runtime:
- Next.js `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- patched PostCSS override `8.5.23`.

Owner Intelligence additionally uses server-side `openpyxl 3.1.5` for controlled XLSX management exports.

Workflow: `Three Crowns Dependency Security Inspection`.
Run: `33242397265`.
Conclusion: `success`.

Committed lockfiles remain in web/admin/staff and production Dockerfiles use deterministic installs.

---

## 6. Migration / database truth

STATUS: **VERIFIED IN CLEAN CI AND CI-LOCAL DOCKER STAGING.**

Committed migration chain:
- `0_init` — canonical core baseline and PostgreSQL invariants;
- `1_site_content` — `site_content_documents`;
- `2_guest_service_tasks` — structured reservation-linked guest-service context on `operational_tasks`.

Verified current facts:
- clean `prisma migrate deploy` succeeds;
- migration ledger is `0_init,1_site_content,2_guest_service_tasks`;
- development seed contains 84 room positions / 12 room categories;
- critical production-preflight PostgreSQL constraints remain present;
- active room/date overlap remains protected by PostgreSQL exclusion constraint;
- payment/date/amount integrity remains database protected;
- Owner Intelligence requires no new persistence tables or parallel reporting database; it reads canonical Resort Core/PostgreSQL facts.

Evidence:
- Production Migration Baseline CI `33242397303` — `success`;
- PostgreSQL Backup Restore CI `33242397193` — `success`;
- Full Staging Gate `33242397283` — `success`.

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

Evidence on audited head:
- Resort Core CI `33242397270` — `success`;
- Payment Idempotency CI `33242397343` — `success`;
- PMS Chessboard Mutation CI `33242397316` — `success`;
- Realtime PMS CI `33242397229` — `success`.

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

The admin API `/api/v1/admin/guest-services` is OWNER/MANAGER scoped, property isolated, reservation linked, validates active `GUARANTEED`/`CHECKED_IN` reservations and rejects duplicate active same reservation/service/date/time.

Creating a guest service does **not** automatically modify `Reservation.totalKgs` or create a `Payment`.

Dedicated evidence:
- Guest Services PMS CI `33242397241` — `success`.

---

## 10. Owner Intelligence / guest database / history / management analytics

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

Current owner-management contour extends the existing Reports/Analytics and canonical Guest/Reservation data rather than creating a second CRM or reporting database.

### Guest identity

Manager confirmation now resolves an existing Guest by normalized property-scoped phone/email before creating a new profile.

Verified fail-closed behavior:
- the same repeat guest with equivalent differently formatted phone/email reuses one Guest profile;
- if phone and email identify different existing profiles, confirmation returns `GUEST_IDENTITY_CONFLICT` and Reservation/Payment are not created;
- if multiple existing profiles already share the same phone or email, confirmation returns `GUEST_IDENTITY_AMBIGUOUS` instead of choosing a profile silently;
- duplicate candidates are surfaced for manual review; automatic historical merge is disabled.

This improves repeat-guest history without claiming a universal probabilistic identity system. Phone/email are evidence, not permission for uncontrolled merging.

### Owner guest database and history

OWNER/MANAGER API under `/api/v1/admin/intelligence` provides:
- guest directory/search;
- reservation count and completed-stay count;
- accumulated room nights;
- stored booked value and RECEIVED payment totals;
- last and next stay dates;
- latest recorded source;
- complete reservation history;
- segmented room history / Split Stay schedule;
- stored payments;
- structured Guest Services;
- linked conversation/channel history;
- property isolation.

Admin UI adds `Гости / История` with guest directory, lifetime management metrics, room segments, payments, services, conversations and duplicate-candidate warnings.

### Occupancy matrix

`/api/v1/admin/intelligence/occupancy-matrix` provides a room-by-day management heatmap for periods up to 93 days:
- every room row;
- every calendar day column;
- Reservation segments;
- maintenance/manual blocks;
- guest/booking context for reservation cells;
- building/floor/category context.

The UI renders this as a scrollable sticky owner heatmap so a month can be inspected by individual room rather than only aggregate occupancy percentage.

### Management exports

`/api/v1/admin/intelligence/export.xlsx` creates an actual XLSX workbook for selected periods up to 367 days.

Verified sheets:
- `Итоги`;
- `Занятость по номерам`;
- `Брони`;
- `Гости`;
- `Платежи`.

The existing analytics UI also retains CSV exports and now provides print/PDF browser output plus comparison with the immediately preceding equal-length period.

Comparison cards include:
- occupancy;
- ADR;
- RevPAR;
- received payments;
- booked room nights;
- CRM conversion.

### Evidence

Dedicated workflow: `Owner Intelligence CI`.
Run: `33242397195`.
Job: `99073867775`.
Conclusion: `success`.

The dedicated E2E verifies on clean PostgreSQL:
- Prisma schema/migrations;
- 84-room / 12-category seed;
- admin TypeScript typecheck and production build;
- Core compile/start;
- two real manager-confirmed Reservations for the same differently formatted guest identity reuse one Guest;
- guest lifetime figures and reservation schedules;
- 84-room occupancy matrix;
- valid XLSX workbook and expected sheets;
- property isolation;
- duplicate-candidate reporting without auto-merge;
- identity-conflict fail-closed rollback with no Reservation or Payment mutation.

These are management/operational analytics. They are **not statutory accounting or tax reporting**.

---

## 11. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts include `Guest`, `ReservationRequest`, `Reservation` and segmented `InventoryBlock` room/date assignments.

Guest identity/repeat-reservation history is now materially stronger through the verified Owner Intelligence resolver and history surface.

A distinct persisted canonical `Stay` entity is still not implemented. Operational stay state is represented primarily through Reservation lifecycle and segmented inventory assignments.

Therefore canonical `Guest != Reservation != Stay` separation is not yet fully implemented. This is a known target/current GAP, not permission for an unreviewed data-model rewrite.

---

## 12. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing is server-side by room type/date using integer KGS values and sale-state controls.

Current Payment domain/CI covers manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Owner Intelligence booked-value / received-payment / ADR / RevPAR figures are management metrics from stored Resort Core facts. They do not transform current finance into statutory accounting.

A complete Folio/Charge/Adjustment/Void/Refund accounting domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 13. Authentication / RBAC / property boundary

STATUS: **VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.**

Current evidence includes Argon2 passwords, hashed session tokens, HttpOnly cookies, expiry/revocation, active-user checks, server-side roles, Property binding and AuditLog authentication evidence.

Owner Intelligence routes are OWNER/MANAGER scoped and dedicated CI proves a foreign-property Guest cannot be read by the current owner session.

Current runtime is property-selected by `PROPERTY_CODE`.

Generic organization/tenant hierarchy, cross-property workflows and universal resource-level multi-property permissions are not established.

External HTTPS cookie/CORS behavior remains an external staging gate.

---

## 14. Operations / Staff PWA

STATUS: **VERIFIED IN CI; REAL-DEVICE ACCEPTANCE OPEN.**

`OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Hotel Operations CI `33242397264` completed `success` and covers owner/maid/technician authorization, housekeeping assignment/state transitions/rework/inspection/CLEAN acceptance, TECH_BLOCK protection, assignment history/workload and application build checks.

Staff Voice CI `33242397233` also completed `success`.

Real iPhone/Android/Telegram Mini App acceptance remains open.

---

## 15. CRM / omnichannel / AI

STATUS: **PARTIAL; REPOSITORY CONTOURS VERIFIED / LIVE PROVIDERS NOT VERIFIED.**

Approved channel boundary:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets -> mirror/control surface only.

Internal AI Sales remains manager-review draft assistance only. AI does not auto-send, confirm payment or create guaranteed Reservations.

Public website AI Administrator is implemented and CI-covered. It uses Core facts/availability, is rate limited, fails explicitly when provider configuration is unavailable, and hands sellable booking intent to the existing ReservationRequest flow.

Evidence on audited head:
- Three Crowns AI Administrator CI `33242397185` — `success`;
- AI Sales Draft CI `33242397236` — `success`;
- n8n Resort Core Contract CI `33242397245` — `success`;
- n8n Workflow JSON CI `33242397213` — `success`;
- Telegram Sales CI `33242397322` — `success`;
- Unified Inbox CI `33242397317` — `success`.

Real OpenAI production credentials, API Green credentials, actual hotel-number webhook/E2E and external HTTPS provider execution remain **NOT VERIFIED / NOT LIVE**.

---

## 16. Public site / owner-approved guest truth

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

Current public site preserves the approved visual direction and current owner-approved guest facts while keeping booking truth in Resort Core.

Current owner-approved facts represented in the site truth contour include:
- current transfer prices supplied by owner;
- current food pricing retained from the approved official-source baseline until a later owner update;
- free parking for staying guests, current owner-approved capacity wording;
- sauna in winter only, 5000 KGS/hour, 4–5 people;
- billiards 500 KGS/hour;
- table tennis free;
- current excursion program subject to manager confirmation/update;
- water activities only as independent seasonal beach operators;
- hotel rules based on owner-provided rules.

Explicit owner rejection/current truth:
- no gym / тренажёрный зал;
- no sports grounds / sports fields / спортивные площадки.

The site keeps the request-not-confirmation boundary and current payment truth. It must not publish stale fixed 30% prepayment, first-night automatic prepayment, two-day unpaid hold, unverified online-card acquiring, unverified Elsom or AI-generated payment instructions.

Evidence:
- Public Site Truth CI `33242397291` — `success`;
- Full Staging Gate `33242397283` — `success`.

The current live legacy `3korony.com` must not be represented as the verified new Resort OS deployment.

---

## 17. Dashboard / analytics / control

STATUS: **IMPLEMENTED AND CI-VERIFIED; NOT EXTERNALLY PRODUCTION-VERIFIED.**

Current Command Center covers occupancy, arrivals/departures, active requests, waiting communications, manager-recorded payments, room attention/states, operations/tasks and finance controls.

Current Reports/Analytics covers:
- date ranges and presets;
- occupancy / available and booked room nights;
- ADR and RevPAR;
- allocated booking value;
- received payments;
- active debtors;
- arrivals/departures;
- in-house/guaranteed reservations;
- CRM funnel/channels;
- room-category performance;
- reservation channels;
- operations;
- daily occupancy dynamics;
- CSV exports;
- previous-period comparison;
- room-by-day occupancy heatmap;
- owner XLSX export;
- print/PDF browser output;
- guest lifetime/history drill-down through the Owner Intelligence surface.

These are management metrics, not statutory accounting/revenue-recognition truth.

Dedicated Owner Intelligence evidence: `33242397195` — `success`.

---

## 18. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository, but active application composition excludes NFC routers.

NFC Deferred Scope CI `33242397292` and Full Staging `33242397283` completed `success`.

Reactivation requires explicit owner decision.

---

## 19. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

Owner Intelligence E2E also proves the management occupancy matrix returns all 84 seeded room rows in the development/CI property.

The production register remains fail-closed until exactly 84 physical room rows and unresolved building/floor/mansard/cottage details are owner-confirmed. Development seed data must not be silently promoted into physical production truth.

---

## 20. Deployment state

### CI-local staging
STATUS: **VERIFIED** on executable head `c9861d4276e7733b9d4e724cf0a7ad4fa2cc3aeb` / associated PR integration context. Run `33242397283` — `success`.

### Single-server deployment package
STATUS: **VERIFIED IN CI.** Run `33242397260` — `success`.

### Purchased hosting / Beget production direction
STATUS: **HOST PLATFORM DIRECTION APPROVED / ACTUAL ACCOUNT AND HOST CAPABILITY NOT VERIFIED.**

The intended autonomy-oriented production direction is Beget infrastructure with application compute, managed PostgreSQL/S3 where selected, self-healing container runtime, health monitoring and controlled backup/restore. No current repository/CI evidence proves that the actual purchased account, VPS resources, DBaaS/S3 configuration, DNS, network or credentials are already provisioned accordingly.

`scripts/host_preflight.sh` remains the required non-destructive first infrastructure test.

### Legacy rollback backup
STATUS: **BLOCKED / NOT VERIFIED.**

No verified full rollback backup of the exact currently live legacy site exists in accessible project evidence. A public crawl or old emergency archive is not sufficient proof of a full rollback point.

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

## 21. High-priority gaps / blockers

### P0 production blockers
1. actual Beget account/server access and non-destructive host capability preflight;
2. verified full rollback backup for the current legacy site;
3. isolated external HTTPS/WSS staging on the real host/network;
4. external rendered public-truth probe against that staging;
5. owner-confirmed physical 84-room register;
6. real iPhone/Android/Telegram acceptance;
7. real website AI browser/mobile acceptance;
8. real provider/WhatsApp/Instagram acceptance for launch-enabled channels;
9. fresh production backup/clean-restore/preflight/secrets/DNS/rollback evidence immediately before cutover.

### P1 product/operations gaps
- safe manual workflow for resolving historical Guest duplicate candidates if owner requires historical cleanup;
- production monitoring/watchdog and backup restore cadence on the actual Beget environment;
- post-stay feedback/NPS/review flow;
- controlled lead follow-up/reactivation flow;
- production marketing analytics destination/attribution.

### P2 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- complete Folio/Charge financial domain;
- universal internal AI Operations Administrator controlled-tool/risk model.

### DEFER
- NFC / beach wallet for current Three Crowns V1.

---

## 22. Foundations to extend rather than rewrite

Preserve unless later evidence proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and exclusion constraint;
- ReservationRequest -> human manager confirmation;
- repeat-Guest fail-closed identity resolver;
- server-authoritative PMS preview/commit;
- V9 universal chessboard composition;
- Owner Intelligence guest/history/reporting surfaces over canonical Core data;
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
- current deployment package until real Beget host evidence proves a required topology change.

---

## 23. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the actual Beget hosting/VPS account, obtain a verified rollback backup of the current legacy site, and—if the host is suitable—deploy an isolated external HTTPS/WSS staging contour before replacing the apex site. Then run the external rendered public-truth probe and complete browser/device acceptance.**

Why this remains next:
- all 24 PR-triggered workflow contours associated with the latest audited executable head are successful;
- Owner Intelligence now covers repeat-guest resolution, guest history, room-by-day owner heatmap and XLSX management exports without introducing a parallel database;
- CI-local Docker staging is verified;
- the one-server production package is verified in CI;
- the three-migration chain is clean-deploy verified;
- PMS move/resize/Split Stay/realtime and structured Guest Services are verified in repository CI;
- public owner-approved guest facts are guarded in CI/local staging;
- the highest-risk unknown is now the actual external Beget host/network/TLS/cookie/CORS/WSS/browser/device environment.

OWNER involvement should be limited to real human-only blockers: Beget account/infrastructure access when unavailable to engineering, physical room-register confirmations, launch secrets/financial/provider approval where required, real-device acceptance and irreversible production cutover approval.

LAST AUDITED EXECUTABLE HEAD: `c9861d4276e7733b9d4e724cf0a7ad4fa2cc3aeb`
LAST AUDITED: 2026-08-29
