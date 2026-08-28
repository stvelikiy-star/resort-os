# RESORT OS — CURRENT STATE

Version: 2.1
Date: 2026-08-28
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

Latest fully audited executable/package head before this documentation-only synchronization:

`19a1228530afcad59a0f3ce19c11f6238e88932a`.

The pull-request workflows associated with that head tested the PR merge snapshot; the Public Site Truth job log records checkout of merge commit `a736aa9fccb56d4c79eb8d7a12f762ead6a75de2` containing head `19a1228530afcad59a0f3ce19c11f6238e88932a` against the PR base.

All 22 associated workflow contours observed for that head completed with conclusion `success`:
- Resort Core CI — `33163003201`;
- Three Crowns Full Staging Gate — `33163003277`;
- Three Crowns Single Server Production Package CI — `33163003205`;
- Three Crowns Dependency Security Inspection — `33163003236`;
- Production Migration Baseline CI — `33163003229`;
- PostgreSQL Backup Restore CI — `33163003219`;
- Control Center Monorepo Contract CI — `33163003193`;
- PMS Chessboard Mutation CI — `33163003218`;
- Realtime PMS CI — `33163003253`;
- Hotel Operations CI — `33163003244`;
- Public Site Truth CI — `33163003199`;
- Three Crowns AI Administrator CI — `33163003186`;
- AI Sales Draft CI — `33163003181`;
- Unified Inbox CI — `33163003206`;
- Telegram Sales CI — `33163003214`;
- Staff Voice CI — `33163003216`;
- Payment Idempotency CI — `33163003203`;
- Automation Contract CI — `33163003194`;
- n8n Resort Core Contract CI — `33163003281`;
- n8n Workflow JSON CI — `33163003187`;
- Data Intake Integrity CI — `33163003195`;
- NFC Deferred Scope CI — `33163003171`.

The current branch may move beyond this audited executable head through documentation-only commits. Such documentation movement does not broaden executable verification.

Current active architecture:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint:
`services/api/app/app_entry.py` -> `app.app_entry:app`.

Current repository surfaces:
- `apps/web` — public Next.js application;
- `apps/admin` — PMS/admin Next.js application;
- `apps/staff` — staff Next.js/PWA;
- `services/api` — FastAPI Resort Core;
- `packages/database` — Prisma/PostgreSQL schema, migrations and critical constraints;
- `automation/n8n` — orchestration workflows/runbooks;
- `deploy` / production compose — one-server Caddy/Docker production package;
- `scripts` — seed, migration, backup/restore, host/staging/release and external-truth checks;
- `knowledge` / `docs` — canonical knowledge and implementation evidence.

---

## 2. CI-local Docker staging

STATUS: **VERIFIED on audited head `19a1228530afcad59a0f3ce19c11f6238e88932a` / associated PR merge snapshot.**

Workflow:
`Three Crowns Full Staging Gate`.

Run:
`33163003277`.

Conclusion:
`success`.

Executed and successful stages include:
1. synthetic staging environment creation;
2. isolated PostgreSQL startup;
3. committed Prisma migration chain application;
4. synthetic Three Crowns seed;
5. migration ledger and database invariant verification;
6. release-scope and public-truth guards;
7. build/start of real FastAPI Core, public web, PMS admin and Staff PWA containers;
8. proof that deployed frontend origins are substantial Resort OS surfaces rather than preview stubs;
9. complete staging acceptance gate;
10. proof that NFC/beach HTTP routes remain absent from active runtime;
11. clean teardown.

This is **CI-local container staging evidence only**. It is not external HTTPS/WSS staging and not production verification.

---

## 3. Single-server production package

STATUS: **VERIFIED IN CI / NOT EXTERNALLY DEPLOYED.**

Workflow:
`Three Crowns Single Server Production Package CI`.

Run:
`33163003205`.

Conclusion:
`success`.

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

The current run successfully validated production Compose/WSS wiring, Caddy configuration, operational shell scripts, pinned n8n image pull and deterministic application image builds.

This does **not** prove that the purchased `3korony.com` hosting is a suitable VPS/VDS or that the package has been deployed there.

---

## 4. Dependency / build security

STATUS: **VERIFIED FOR THE CURRENT LOCKED FRONTEND TREE IN CI.**

Current declared frontend runtime remains:
- Next.js `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- patched PostCSS override `8.5.23`.

Committed lockfiles exist for web/admin/staff; production Dockerfiles use `npm ci`.

Workflow:
`Three Crowns Dependency Security Inspection`.

Run:
`33163003236`.

Conclusion:
`success`.

Executed checks include committed-lockfile presence, matching runtime versions across all three Next apps, lockfile/package-manifest consistency, exact audit capture, and high/critical vulnerability gate.

Existing GitHub-hosted action runtime deprecation warnings are tooling warnings and are not represented as application runtime verification failures.

---

## 5. Migration / database truth

STATUS: **VERIFIED IN CLEAN CI AND CI-LOCAL DOCKER STAGING.**

Committed migration chain:
- `0_init` — canonical baseline with core schema and critical PostgreSQL invariants;
- `1_site_content` — forward migration for `site_content_documents`.

Verified current facts remain:
- `prisma migrate deploy` succeeds on clean PostgreSQL;
- migration ledger contains `0_init,1_site_content`;
- `site_content_documents` exists after migration;
- 84 development room positions / 12 room categories seed successfully;
- 13 critical database constraints are present;
- active room/date overlap is protected by PostgreSQL GiST exclusion constraint;
- payment/date/amount integrity checks remain present.

Current exact-head evidence:
- Production Migration Baseline CI `33163003229` — `success`;
- PostgreSQL Backup Restore CI `33163003219` — `success`;
- Full Staging Gate `33163003277` — migration/database invariant stages `success`.

Production database itself has not yet been migrated or proven by this evidence.

---

## 6. Reservation / availability / PMS

STATUS: **VERIFIED FOR CURRENT THREE CROWNS V1 FLOW IN CI.**

Canonical active boundary:

`ReservationRequest -> manager/human confirmation -> Reservation`.

Current verified rules:
- `ReservationRequest != Reservation`;
- request creation does not itself guarantee or hold a confirmed reservation;
- no authoritative global automatic prepayment percentage exists for Three Crowns V1;
- manager chooses payment amount/terms/method and records accepted payment fact;
- AI/n8n cannot directly create a guaranteed Reservation or confirm payment;
- availability and pricing are server-authoritative Core facts.

Resort Core CI `33163003201` successfully executed:
- Admin/Web/Staff builds;
- public availability and ReservationRequest creation;
- protected PMS/login;
- unified Site CMS/CRM/PMS contour;
- quote without automatic prepayment rule;
- manager-confirmed manual payment -> Reservation atomically;
- payment idempotency;
- Reservation visibility in PMS;
- check-in -> checkout -> housekeeping lifecycle.

PMS Chessboard Mutation CI `33163003218` successfully executed:
- Admin build;
- manager-confirmed guaranteed Reservation setup;
- canonical schedule read;
- whole-booking move preview/commit;
- stale manager snapshot rejection with unchanged schedule;
- resize and Split Stay across two rooms;
- CLEAN requirement for check-in;
- immediate relocation preserving lived history and dirtying the vacated room;
- conflict rollback preserving valid schedule;
- checkout from actual current room with housekeeping creation;
- AuditLog evidence.

Realtime PMS CI `33163003253` also completed `success`.

Database overlap protection remains the final double-booking guard.

---

## 7. PMS V9 / universal chessboard current UI

STATUS: **IMPLEMENTED AND COVERED BY THE VERIFIED PMS/CORE CONTOURS ABOVE.**

The primary daily PMS surface is the V9 composition:
- `PMSOperationsCockpitV9`;
- `PMSBulkGuardV9`;
- `PMSUniversalBoard`;
- shared `PMSControlSnapshotProviderV9`.

`PMSUniversalBoard` currently implements, rather than merely plans:
- search by guest/phone/booking/room/category/building context;
- room type/building/floor/room-state/reservation-state filters;
- finance/debt, occupancy and block-type filters;
- quick views for arrivals, departures, in-house, free, debt and attention;
- grouping by building, floor or category;
- compact/comfortable density;
- 7/14/21/31-day windows;
- HTTP polling plus PMS realtime WebSocket;
- whole-booking drag/move for allowed future state;
- segment move;
- Split Stay / scissors interaction;
- server preview before commit;
- TECH_BLOCK destination protection;
- checked-in history protection;
- unassigned guaranteed-reservation placement;
- finance filters that fail closed when the financial read model is unavailable/incomplete.

Therefore the earlier owner request for a universal chessboard with strong filtering, movement and split-stay handling is **not an unimplemented blank-slate task**. Future work must extend this surface rather than create a parallel replacement unless a concrete defect is proven.

---

## 8. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts currently include:
- `Guest`;
- `ReservationRequest`;
- `Reservation`;
- segmented `InventoryBlock` room/date assignments.

A distinct persisted canonical `Stay` entity is not implemented in the current Prisma model. Operational stay state is represented primarily through Reservation lifecycle plus segmented inventory assignments.

Canonical `Guest != Reservation != Stay` separation is therefore not fully implemented.

This is a target/current GAP, not evidence that the verified Three Crowns V1 flow is broken. Do not perform an automatic data-model rewrite before Stay business rules and migration consequences are approved.

---

## 9. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing supports server-side rate periods by room type/date using integer KGS values and explicit sale states.

Current Payment model/CI cover manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Current finance is operational payment control, not statutory accounting.

A complete canonical Folio/Charge/Adjustment/Void/Refund domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 10. Authentication / RBAC / property boundary

STATUS: **VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.**

Current evidence includes:
- Argon2 passwords;
- random session tokens persisted only as SHA-256 hashes;
- HttpOnly cookies;
- expiry/revocation;
- active-user checks;
- server-side role dependencies;
- Property binding;
- AuditLog on authentication actions.

Current Three Crowns runtime is property-selected by `PROPERTY_CODE`.

Generic organization/tenant hierarchy, cross-property workflows and a universal resource-level permission model remain future architecture work.

External HTTPS cookie/CORS behavior still requires deployed staging verification.

---

## 11. Operations / Staff PWA

STATUS: **VERIFIED IN CURRENT CI CONTOUR; REAL-DEVICE ACCEPTANCE OPEN.**

Current `OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Hotel Operations CI `33163003244` completed `success` and executed:
- Core compile/release-scope checks;
- owner/maid/technician authentication;
- staff overview;
- housekeeping task creation/assignment;
- rejection of skipped state transition;
- maid claim -> inspection;
- manager rework -> maid resubmission -> manager CLEAN acceptance;
- proof that TECH_BLOCK cannot be silently cleaned by housekeeping;
- assignment history/workload checks;
- PMS and Staff PWA builds.

Real iPhone/Android/Telegram Mini App acceptance remains open.

---

## 12. CRM / omnichannel / AI

STATUS: **PARTIAL; PUBLIC WEBSITE AI ADMINISTRATOR VERIFIED IN CI / LIVE PROVIDER DELIVERY NOT VERIFIED.**

Approved Three Crowns V1 channel boundary remains:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets -> mirror/control surface, not hotel source of truth.

Internal AI Sales remains manager-review draft assistance only:
- OWNER/MANAGER access;
- Core facts loaded server-side;
- guest conversation treated as untrusted content;
- no auto-send;
- no payment/reservation-confirmation authority;
- output stored as INTERNAL `AI_DRAFT` with audit evidence.

Public website AI Administrator is implemented:
- globally mounted responsive widget;
- browser calls Resort Core directly via `/core/api/v1/public/ai-admin/chat`;
- explicit date/adult/child search;
- exact availability/pricing comes from existing Core availability logic;
- only sellable options with integer `total_kgs` are exposed;
- hotel facts/current availability are prepared server-side before LLM composition;
- public rate limiting;
- provider-not-configured fails with `503`;
- provider failures fail explicitly;
- no Reservation confirmation/payment confirmation/prepayment-setting/payment-link authority;
- sellable availability hands off to existing `#booking` ReservationRequest flow.

Current exact-head AI Administrator evidence:
- run `33163003186` — `success`;
- deterministic public-web dependency check;
- public web typecheck/build;
- Core AI module compile;
- WhatsApp n8n authority-boundary validation;
- proof website stays Core-direct;
- production env/Compose wiring check.

WhatsApp/API Green repository workflow/configuration is not equivalent to live delivery. Real OpenAI production credentials, API Green credentials, hotel-number webhook/E2E and external HTTPS execution remain **NOT VERIFIED / NOT LIVE**.

A universal internal AI Operations Administrator controlled-tool layer is not yet implemented.

---

## 13. Public site / CMS / public-truth safety

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

Current public web includes:
- premium Three Crowns presentation;
- 12-category room catalog/pages;
- Core-backed availability/pricing;
- ReservationRequest submission;
- explicit request-not-booking boundary;
- RU/KG/EN runtime;
- CMS content storage/read boundary;
- privacy-safe booking-funnel analytics events;
- metadata/SEO routes;
- repository-local property media baseline;
- public AI Administrator.

Public Site Truth CI `33163003199` completed `success` on the current audited head. Its real job steps executed:
- canonical public sales boundary guard;
- external rendered-site truth-probe unit tests;
- RU/KG/EN locale contract guard.

Observed log evidence:
- protected public files: `12`;
- public room categories: `12`;
- analytics allowlist: present;
- public truth guard: PASS;
- external truth probe tests: `6` tests, all OK;
- localized room categories: `12`;
- locales: `ru,kg,en`;
- i18n guard: PASS.

The public-truth guard now fail-closes on stale/unapproved public claims including:
- fixed 30% prepayment;
- stale two-day unpaid hold;
- fixed first-night prepayment;
- unverified online card-acquiring claim;
- unverified Elsom payment route;
- other explicitly non-canonicalized public amenity/media claims already protected by the guard.

`scripts/external_public_truth_probe.py` is implemented and unit-tested as a non-destructive external acceptance tool. It:
- requires HTTPS by default;
- rejects credentials embedded in the URL;
- bounds response size;
- requires HTML/XHTML;
- applies the protected forbidden-claim patterns to rendered external HTML;
- requires key rendered booking/public-truth snippets;
- returns explicit PASS / drift / blocked results.

**The existence and CI verification of this probe does not verify any external URL.** It must be run against isolated external staging and again after controlled cutover.

The currently live legacy `3korony.com` must not be treated as the verified new Resort OS deployment.

---

## 14. Dashboard / analytics / control

STATUS: **IMPLEMENTED + CI-COVERED; NOT PRODUCTION-VERIFIED.**

Current Command Center includes current occupancy, arrivals, departures, active booking requests, communications waiting, manager-recorded payments, room-attention counts, room states, operations/tasks, finance controls and drill-down navigation.

Current Reports/Analytics includes selectable date ranges and management metrics for:
- occupancy / room nights;
- ADR;
- RevPAR;
- allocated booking value;
- received payments;
- active debtors;
- arrivals/departures;
- in-house / guaranteed reservations;
- CRM conversion/funnel;
- CRM channels;
- room-category performance;
- reservation channels;
- housekeeping/maintenance/guest-request operations;
- daily occupancy dynamics;
- CSV exports for supported report sets.

Management allocation metrics are explicitly not represented as statutory accounting/revenue-recognition truth.

Therefore the prior owner request for Dashboard/Analytics/Control/operational numbers has a substantial implemented current surface. Further work should be evidence-driven refinement, not a second independent dashboard.

---

## 15. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository.

Active application composition intentionally excludes NFC routers.

Current Full Staging Gate `33163003277` successfully verified that NFC routes remain absent from active runtime.

Reactivation requires explicit owner decision.

---

## 16. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

Google Drive contains the fail-closed production register:
`НОМЕРНОЙ ФОНД — Три Короны — Production Import 84`.

`OWNER_CHECKLIST` still contains unresolved factual questions about specific buildings/floors, mansard rooms, cottages and several room groups. Those facts must not be guessed.

`scripts/import_physical_rooms.py` remains dry-run/fail-closed and requires exactly 84 owner-confirmed room rows before production reconciliation.

Development 84/12 data is therefore not yet owner-approved physical production truth.

---

## 17. Deployment state

### CI-local staging

STATUS: **VERIFIED on audited head `19a1228530afcad59a0f3ce19c11f6238e88932a` / associated PR merge snapshot.**

Run `33163003277` passed the complete isolated Docker topology and acceptance.

### Single-server deployment package

STATUS: **VERIFIED IN CI.**

Run `33163003205` completed `success`.

### Purchased `3korony.com` hosting

STATUS: **UNKNOWN / BLOCKED ON HOST ACCESS.**

There is no current evidence establishing whether the purchased hosting is shared hosting or a VPS/VDS with sufficient CPU/RAM/disk/root/Docker capability.

`scripts/host_preflight.sh` is implemented and non-destructive. It checks Linux/architecture, CPU, RAM, disk, root/sudo, Docker/Compose, outbound registry connectivity, ports 80/443, host-level 5432 exposure, persistent target-path access and existing web services; it returns PASS / PASS WITH WARNINGS / BLOCKED without installing, stopping or overwriting services.

The currently live legacy site must remain intact until a backup/rollback point exists and the new external staging passes acceptance.

### External HTTPS/WSS staging

STATUS: **BLOCKED / NOT VERIFIED.**

The actual purchased host has not been inspected/deployed through available project tooling. Real TLS, secure cookies, CORS, WSS upgrade, network/firewall, real browser and real-device behavior remain unproven.

### Live AI / messaging providers

STATUS: **BLOCKED / NOT VERIFIED.**

Repository code/configuration does not prove real OpenAI production credentials, API Green credentials, actual provider webhook delivery or hotel-number WhatsApp E2E.

### Production

STATUS: **NOT PRODUCTION READY.**

No CI result alone authorizes production DNS cutover.

---

## 18. High-priority gaps / blockers

### P0 production blockers
1. purchased host capability/access + non-destructive preflight;
2. verified backup/rollback point for the current legacy site;
3. isolated external HTTPS/WSS staging on the real host;
4. run external rendered public-truth probe against that staging;
5. owner-confirmed physical 84-room register;
6. real iPhone/Android/Telegram acceptance;
7. real website AI browser/mobile acceptance;
8. real provider/WhatsApp acceptance if those provider contours are activated for launch;
9. fresh production backup/clean-restore/preflight/secrets/DNS/rollback evidence immediately before cutover.

### P1 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- complete Folio/Charge financial domain;
- universal internal AI Operations Administrator controlled-tool/risk model.

### VALIDATE / DECISION REQUIRED
- generic reservation/stay lifecycle beyond property-specific V1;
- generic pricing/children/extra-bed rules;
- Folio/refund/void rules;
- Partner/Agent commissions/settlements;
- Service/Resource scheduling;
- payment-provider strategy;
- complete AI tool/approval matrix;
- live omnichannel provider verification.

### DEFER
- NFC / beach wallet for current Three Crowns V1.

---

## 19. Foundations to extend rather than rewrite

Preserve unless later evidence proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and exclusion constraint;
- ReservationRequest -> human manager conversion;
- server-authoritative PMS schedule preview/commit;
- V9 universal chessboard composition;
- payment idempotency;
- AuditLog pattern;
- property-scoped staff session/RBAC baseline;
- OperationalTask engine;
- read-only CRM mirror boundary;
- n8n orchestration without direct DB authority;
- public site using Core availability/pricing/request creation;
- public AI website using Core facts/availability without Reservation/payment authority;
- public truth fail-closed guards and external acceptance probe;
- Command Center/Reports current management surfaces;
- dormant NFC isolation;
- single-server production package unless actual hosting evidence proves a concrete limitation.

---

## 20. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the purchased `3korony.com` hosting, preserve/backup the current live site, and—if the host is suitable—deploy an isolated external HTTPS/WSS staging contour before replacing the apex site. Then run the external rendered public-truth probe and complete browser/device acceptance.**

Why this remains next:
- current audited integration head has all 22 observed associated CI workflow contours successful;
- CI-local Docker staging is verified;
- the one-server production package is verified in CI;
- PMS move/resize/Split Stay and operations are verified in executable CI;
- Dashboard/Analytics/Control already have substantial implemented surfaces;
- public-payment/sales truth is now hardened fail-closed in repository CI;
- the remaining highest-risk unknown is the real host/network/TLS/cookie/CORS/WSS/browser/device environment;
- adding unrelated features before resolving that P0 would increase surface area without reducing launch risk.

OWNER involvement should be limited to missing factual/access inputs: hosting access when unavailable to engineering, physical room-register confirmations, launch-approved provider secrets, real-device acceptance and irreversible production approval.

LAST AUDITED: 2026-08-28
