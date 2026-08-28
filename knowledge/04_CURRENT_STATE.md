# RESORT OS — CURRENT STATE

Version: 2.0
Date: 2026-08-28
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL DOCKER STAGING VERIFIED / SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: factual implementation reality only

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL STAGING VERIFIED != EXTERNAL STAGING VERIFIED != PRODUCTION VERIFIED.**

This document describes factual implementation evidence for the current Three Crowns integration candidate. It does not redefine Product Bible, Domain Business Rules, target architecture or AI governance.

---

## 1. Audited baseline

Repository: `stvelikiy-star/resort-os`.

Integration branch: `integration/site-pms-cms-20260827`.

Open integration PR: `#37 — Unify site, V9 PMS/CRM, analytics, staff and staging through Resort Core`.

Fully audited executable/package code head: `be6809381220444ff663bdf82aec65a0ea9b1e06`.

On that code head all 21 associated workflow contours completed with conclusion `success`, including Resort Core, Full Staging Gate, Single Server Production Package, dependency security, migration baseline, backup/restore, Control Center, PMS/realtime/operations, public truth, automation/n8n, staff voice, Telegram, AI Sales, inbox, data intake and NFC deferred-scope checks.

A later, narrower public AI Administrator increment is separately audited on executable head `731cf9114d860d9625901f5ba5cfd48cdc756540`.

Verified evidence for that increment:
- workflow: `Three Crowns AI Administrator CI`;
- run id: `33160438772`;
- head SHA: `731cf9114d860d9625901f5ba5cfd48cdc756540`;
- conclusion: `success`;
- job steps are present and completed successfully, including deterministic public-web dependencies, web typecheck/build, Core AI module compile, WhatsApp n8n authority-boundary validation, Core-direct website routing and production env/Compose wiring.

The current branch head may contain later documentation-only commits. Documentation movement does not broaden executable verification beyond the exact audited code heads above.

Current active architecture:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint: `services/api/app/app_entry.py` -> `app.app_entry:app`.

Integration composition version: `0.34.0`.

Current repository surfaces:
- `apps/web` — public Next.js application;
- `apps/admin` — PMS/admin Next.js application;
- `apps/staff` — staff Next.js/PWA;
- `services/api` — FastAPI Resort Core;
- `packages/database` — Prisma/PostgreSQL schema, migrations and critical constraints;
- `automation/n8n` — orchestration workflows/runbooks;
- `deploy` / production compose — one-server Caddy/Docker production package;
- `scripts` — seed, migration, backup/restore, host/staging/release checks;
- `knowledge` / `docs` — canonical and implementation evidence.

---

## 2. CI-local Docker staging verification

STATUS: **VERIFIED on audited code head `be6809381220444ff663bdf82aec65a0ea9b1e06`.**

GitHub Actions:
- workflow: `Three Crowns Full Staging Gate`;
- run id: `33154426108`;
- conclusion: `success`.

The gate uses an isolated synthetic staging environment and does not require production guest/payment data.

Verified executed steps:
1. isolated PostgreSQL container start;
2. committed Prisma migration chain application with `prisma migrate deploy`;
3. synthetic Three Crowns seed and OWNER/MAID/TECHNICIAN bootstrap;
4. migration ledger, 84-room/12-category baseline and critical DB-invariant checks;
5. release-scope, public-truth and i18n guards;
6. Docker build and start of real FastAPI Core + public web + PMS admin + staff PWA;
7. proof that all three frontend origins return substantial Resort OS application surfaces rather than preview stubs;
8. complete `scripts/staging_full_gate.py` acceptance;
9. active-runtime OpenAPI check proving NFC/beach HTTP routes are not composed;
10. clean teardown.

This is strong repository-level composition evidence. It is still **CI-local container staging**, not an external HTTPS/WSS deployment and not production proof.

---

## 3. Single-server production package

STATUS: **VERIFIED IN CI / NOT EXTERNALLY DEPLOYED.**

The approved Three Crowns deployment simplification is now implemented as one VPS/VDS production package rather than a mandatory Vercel/Supabase/Replit dependency chain.

Intended one-server runtime:
- Caddy on public ports 80/443/443-UDP;
- public Next.js web;
- PMS/Admin Next.js;
- Staff PWA;
- FastAPI Resort Core;
- private PostgreSQL;
- n8n automation client;
- persistent host media / PostgreSQL / n8n state;
- local backup directory with off-site copy expected outside the server.

GitHub Actions:
- workflow: `Three Crowns Single Server Production Package CI`;
- run id: `33154426092`;
- conclusion: `success`.

Verified by that run:
- production Docker Compose graph renders successfully;
- PostgreSQL is not published through host port 5432;
- Admin build receives `NEXT_PUBLIC_CORE_WS_URL=wss://api.3korony.com`;
- Caddy configuration validates;
- `scripts/production_backup.sh` and `scripts/host_preflight.sh` pass shell validation;
- pinned `n8nio/n8n:2.36.2` image is pullable;
- API/web/admin/staff production Docker images build successfully from committed dependency locks using `npm ci`.

This does **not** prove that the currently purchased `3korony.com` hosting is a suitable VPS/VDS. That remains an external host fact.

---

## 4. Production dependency/security hardening

STATUS: **VERIFIED FOR THE CURRENT LOCKED NEXT RUNTIME TREE.**

Current frontend runtime declarations:
- Next.js `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- explicit PostCSS override `8.5.23`.

The production build audit originally exposed a high-severity transitive PostCSS advisory in the Next 15 dependency tree. The remediation was implemented as an explicit patched PostCSS override without forcing an unrelated Next 16 architecture upgrade.

Committed `package-lock.json` files now exist for web/admin/staff and production Dockerfiles use deterministic `npm ci`.

GitHub Actions:
- workflow: `Three Crowns Dependency Security Inspection`;
- run id: `33154426079`;
- conclusion: `success`.

Exact audit metadata on the audited code head:
- info: 0;
- low: 0;
- moderate: 0;
- high: 0;
- critical: 0;
- total: 0.

The dependency-security workflow uses read-only repository permission and verifies committed lockfiles rather than mutating the integration branch.

n8n production baseline is explicitly pinned to `2.36.2`, a release at/above the remediation floor for the reviewed 2026 high-severity n8n advisories. `latest` is not the production default.

GitHub-hosted action warnings about Node 20 action-runtime deprecation remain ecosystem/tooling warnings and are not evidence of an application runtime vulnerability. They should be migrated when supported action majors are reviewed.

---

## 5. Migration / database truth

STATUS: **VERIFIED IN CLEAN CI AND CI-LOCAL DOCKER STAGING.**

Current committed migration chain:
- `0_init` — canonical baseline with core schema and critical PostgreSQL invariants;
- `1_site_content` — forward migration for `site_content_documents`.

The second migration was added after the production-like staging gate correctly exposed a migration gap that normal development `prisma db push` had masked. The fix was implemented as a forward migration; `0_init` was not rewritten.

Verified current facts:
- `prisma migrate deploy` succeeds on clean PostgreSQL;
- migration ledger contains `0_init,1_site_content`;
- `site_content_documents` exists after migration;
- 84 development room positions / 12 room categories seed successfully;
- 13 critical database constraints are present;
- active room/date overlap remains protected by PostgreSQL GiST exclusion constraint;
- payment/date/amount integrity checks remain present.

`Production Migration Baseline CI` run `33154426088` succeeds on the two-migration chain.

`PostgreSQL Backup Restore CI` run `33154426085` verifies migration-aware backup -> clean restore -> matching migration ledger and critical constraints.

Production database itself has not yet been migrated or proven by this CI evidence.

---

## 6. Reservation / availability / PMS truth

STATUS: **VERIFIED FOR CURRENT THREE CROWNS V1 FLOW.**

Canonical active boundary remains:

`ReservationRequest -> manager/human confirmation -> Reservation`.

Verified rules:
- `ReservationRequest != Reservation`;
- request creation does not itself hold inventory;
- no authoritative global automatic prepayment percentage exists;
- manager chooses payment amount/terms/method and records accepted payment fact;
- n8n/AI cannot directly create guaranteed Reservation or confirm payment;
- availability and pricing are server-authoritative Core facts.

PMS V9 remains the primary daily operating surface while mutations are server-authoritative.

Verified schedule capabilities include:
- room/date move;
- resize;
- Split Stay / segmented room assignment;
- partial relocation from an effective date;
- stale snapshot rejection;
- conflict rollback;
- TECH_BLOCK protection;
- CLEAN requirement for immediate destination room;
- vacated room -> DIRTY plus housekeeping creation/reuse;
- server price-impact preview;
- explicit manager commit;
- AuditLog evidence;
- realtime PMS contract.

The current production package explicitly supplies the Admin client with the public Core WSS origin. Caddy routes the API host to FastAPI; external WSS behavior must still be proven on the actual HTTPS host.

Database overlap protection remains the final double-booking guard.

---

## 7. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts currently include:
- `Guest`;
- `ReservationRequest`;
- `Reservation`;
- segmented `InventoryBlock` room/date assignments.

A distinct persisted canonical `Stay` entity is not implemented in the current Prisma model. Operational stay state is represented primarily through Reservation lifecycle plus segmented inventory assignments.

Therefore canonical `Guest != Reservation != Stay` separation is not fully implemented.

This is an architectural target/current GAP, not evidence that current Three Crowns V1 booking/check-in/check-out flow is broken. Do not perform an automatic rewrite before Stay business rules and migration consequences are approved.

---

## 8. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing supports server-side rate periods by room type/date using integer KGS values and explicit sale states.

Current Payment model and CI cover manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Current finance is operational payment control, not statutory accounting.

A complete canonical Folio/Charge/Adjustment/Void/Refund domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 9. Authentication / RBAC / property boundary

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

## 10. Operations / Staff PWA

STATUS: **VERIFIED IN CURRENT CI CONTOUR; REAL-DEVICE ACCEPTANCE OPEN.**

Current `OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Verified safeguards include assignment/claim rules, controlled task transitions, housekeeping inspection, TECH_BLOCK protection, maintenance -> DIRTY/housekeeping behavior and audit history.

Integration Staff PWA V2 includes mobile `Моя смена`, housekeeping checklist/report and technician completion reporting.

Automated/container verification does not replace real iPhone/Android/Telegram Mini App acceptance.

---

## 11. CRM / omnichannel / AI

STATUS: **PARTIAL; PUBLIC WEBSITE AI ADMINISTRATOR VERIFIED IN CI / LIVE PROVIDER DELIVERY NOT VERIFIED.**

Current approved Three Crowns channel boundary:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets is a mirror/control surface, not hotel source of truth.

Core contains property-scoped conversation/message models and protected automation contracts.

Existing internal AI Sales contour remains manager-review draft assistance:
- OWNER/MANAGER access;
- Core facts loaded server-side;
- guest conversation treated as untrusted content;
- no auto-send;
- no payment/reservation confirmation authority;
- output stored as INTERNAL `AI_DRAFT`;
- AuditLog evidence.

A separate public website AI Administrator contour is implemented on audited executable head `731cf9114d860d9625901f5ba5cfd48cdc756540`:
- globally mounted responsive website widget;
- browser calls Resort Core directly through `/core/api/v1/public/ai-admin/chat`;
- explicit check-in/check-out/adults/children availability search;
- availability/pricing is obtained from the existing server-authoritative Core availability path;
- only sellable options with integer `total_kgs` are exposed as current price options;
- hotel facts and current availability are constructed server-side before LLM response composition;
- guest conversation is treated as untrusted content;
- public request rate limiting is implemented;
- missing OpenAI provider configuration fails with `503` rather than fabricating an answer;
- provider transport/rejection failures fail explicitly rather than being represented as success;
- AI cannot confirm Reservation, confirm payment, choose prepayment amount/terms/method or invent payment links/QR;
- when sellable availability exists, the widget hands off to the existing `#booking` flow, which creates a `ReservationRequest` rather than a guaranteed Reservation.

Dedicated evidence:
- workflow: `Three Crowns AI Administrator CI`;
- run id: `33160438772`;
- exact head: `731cf9114d860d9625901f5ba5cfd48cdc756540`;
- conclusion: `success`;
- executed job steps include web dependency verification, public web typecheck/build, Core AI module compile, WhatsApp n8n authority-boundary validation, Core-direct website routing and production env/Compose wiring.

WhatsApp/API Green workflow/configuration exists in the repository boundary but real production credentials, real provider webhook delivery, real hotel-number E2E behavior and external HTTPS execution remain **NOT VERIFIED / NOT LIVE**.

The public AI website contour is therefore **VERIFIED IN CI**, not production verified.

A universal internal AI Operations Administrator controlled-tool layer is not yet implemented.

---

## 12. Public site / CMS / analytics

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL VISUAL/MEDIA ACCEPTANCE OPEN.**

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
- public AI Administrator widget verified separately on executable head `731cf9114d860d9625901f5ba5cfd48cdc756540`.

The production-like staging gate exposed and then verified the missing CMS migration. Public/CMS smoke succeeds after clean `migrate deploy` on the fully audited integration baseline.

The existing Vercel project `three-crowns-v3-preview` is only a simple preview/stub and is **not** accepted as Resort OS staging evidence.

---

## 13. Dashboard / analytics

STATUS: **IMPLEMENTED + CI-COVERED; NOT PRODUCTION-VERIFIED.**

Current management reporting includes occupancy/room nights, management ADR/RevPAR, received payments/current debtors, arrivals/departures, CRM funnel/channels, 12-category performance and operations metrics.

Management allocation metrics are explicitly not represented as statutory accounting/revenue-recognition truth.

---

## 14. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository.

The active application composition intentionally excludes NFC routers.

The full staging gate directly verifies that active OpenAPI exposes no NFC/beach HTTP routes.

Reactivation requires explicit owner decision.

---

## 15. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

Google Drive contains the fail-closed production register:
`НОМЕРНОЙ ФОНД — Три Короны — Production Import 84`.

`OWNER_CHECKLIST` still contains unresolved factual questions about specific buildings/floors, mansard rooms, cottages and several room groups. Those facts must not be guessed.

`scripts/import_physical_rooms.py` remains dry-run/fail-closed and requires exactly 84 owner-confirmed room rows before production reconciliation.

Therefore development 84/12 data is not yet owner-approved physical production truth.

---

## 16. Deployment state

### CI-local staging

STATUS: **VERIFIED.**

Audited run `33154426108` passed the complete isolated Docker topology and acceptance on clean migrations with synthetic data.

### Single-server deployment package

STATUS: **VERIFIED IN CI.**

Audited run `33154426092` proves the approved one-VPS package is syntactically/build-valid, has pinned n8n, deterministic frontend builds, private PostgreSQL and explicit PMS WSS wiring.

### Purchased `3korony.com` hosting

STATUS: **UNKNOWN / BLOCKED ON HOST ACCESS.**

The project does not yet have evidence whether the currently purchased hosting is shared hosting or a VPS/VDS with sufficient CPU/RAM/disk/root/Docker capability.

`scripts/host_preflight.sh` is implemented specifically for this gate. It is non-destructive and reports PASS / PASS WITH WARNINGS / BLOCKED without installing, stopping or overwriting anything.

The currently live legacy `3korony.com` must remain intact until it has been backed up and the new system passes staging acceptance.

### External HTTPS/WSS staging

STATUS: **BLOCKED / NOT VERIFIED.**

The actual purchased host has not yet been inspected/deployed. Real TLS, secure cookies, CORS, WSS upgrade, network/firewall and device behavior remain unproven.

Do not substitute Vercel/Replit preview evidence for the approved one-server external acceptance.

### Live AI / messaging providers

STATUS: **BLOCKED / NOT VERIFIED.**

Repository code/configuration does not prove real OpenAI production credentials, API Green credentials, actual webhook delivery, actual hotel-number WhatsApp E2E, prompt-injection handling in the live provider path, or external browser/mobile AI acceptance.

### Production

STATUS: **NOT PRODUCTION READY.**

Remaining production blockers:
1. actual purchased hosting must pass host preflight or be upgraded to suitable VPS/VDS;
2. existing live site must have a verified backup and rollback point before any replacement;
3. owner-confirmed physical 84-room register;
4. isolated external HTTPS/WSS staging on the actual host and complete acceptance;
5. real iPhone/Android/Telegram acceptance;
6. real website AI Administrator browser/mobile acceptance;
7. real OpenAI/API Green secrets and WhatsApp E2E acceptance if those provider contours are activated for launch;
8. fresh production backup/clean-restore proof immediately before cutover;
9. production secrets, controlled DNS/apex cutover and documented rollback evidence.

No CI result alone authorizes production DNS cutover.

---

## 17. High-priority target/current gaps

### P0 / production blockers
- purchased host capability/access + non-destructive preflight;
- preserve/back up current legacy site before replacement;
- external HTTPS/WSS staging environment and acceptance;
- owner physical 84-room confirmation;
- real-device mobile/Telegram acceptance;
- external website AI acceptance and, if enabled for launch, real provider/WhatsApp acceptance;
- final production backup/preflight/secrets/DNS/rollback evidence.

### P1 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- full Folio/Charge financial domain;
- complete universal internal AI Operations Administrator controlled-tool/risk model.

### VALIDATE / DECISION REQUIRED
- generic reservation/stay lifecycle beyond property-specific implementation;
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

## 18. Foundations that should be extended, not rewritten without evidence

Preserve unless a later audit proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and exclusion constraint;
- ReservationRequest -> human manager conversion;
- server-authoritative PMS schedule preview/commit;
- payment idempotency;
- AuditLog pattern;
- property-scoped staff session/RBAC baseline;
- OperationalTask engine;
- read-only CRM mirror boundary;
- n8n orchestration without direct DB authority;
- public site using Core availability/pricing/request creation;
- public AI website using Core facts/availability without Reservation/payment authority;
- dormant NFC isolation;
- single-server production package unless actual hosting evidence proves a concrete limitation.

---

## 19. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the currently purchased `3korony.com` hosting, preserve the existing live site, and—if the host is suitable—deploy an isolated external staging contour on that same server before replacing the apex site.**

Why this is next:
- the fully audited executable integration baseline has all 21 associated workflow contours successful;
- the later public AI Administrator increment has its own successful dedicated CI evidence on exact head `731cf9114d860d9625901f5ba5cfd48cdc756540`;
- current full Docker staging gate is successful on the full audited baseline;
- current one-server production package is CI-verified;
- dependency audit is zero on the exact locked frontend tree;
- migration and backup/restore chains are verified;
- the remaining highest-risk unknown is the real purchased host/network/TLS/cookie/CORS/WSS/device environment;
- adding unrelated features now would increase surface area without reducing launch risk.

Owner involvement should remain limited to providing/accessing the hosting account if no connector exists, factual room-register confirmations, real provider secrets where launch activation is approved, and real-device acceptance. Technical deployment execution remains an engineering task.

LAST AUDITED: 2026-08-28
