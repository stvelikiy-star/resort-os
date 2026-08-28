# RESORT OS — CURRENT STATE

Version: 1.8
Date: 2026-08-28
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL DOCKER STAGING VERIFIED / EXTERNAL STAGING NOT VERIFIED / NOT PRODUCTION READY
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

Current verified staging-gate code head: `9b5c21293704a8573a904c2bf25221348a21a9bd`.

Current architecture:

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
- `scripts` — seed, migration, backup/restore, staging/release checks;
- `knowledge` / `docs` — canonical and implementation evidence.

---

## 2. CI-local Docker staging verification

STATUS: **VERIFIED on commit `9b5c21293704a8573a904c2bf25221348a21a9bd`.**

GitHub Actions run:
- workflow: `Three Crowns Full Staging Gate`;
- run id: `33142971361`;
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

This is stronger evidence than individual build/unit contracts because the complete repository applications are composed together against a clean migrated PostgreSQL database.

It is still **CI-local container staging**, not an external HTTPS/WSS deployment and not a production proof.

---

## 3. Migration / database truth

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

`Production Migration Baseline CI` succeeds on the two-migration chain.

`PostgreSQL Backup Restore CI` also succeeds after the forward migration and verifies migration-aware backup -> clean restore -> matching migration ledger and critical constraints.

Production database itself has not yet been migrated or proven by this CI evidence.

---

## 4. Reservation / availability / PMS truth

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

Database overlap protection remains the final double-booking guard.

---

## 5. Guest / Reservation / Stay gap

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

## 6. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing supports server-side rate periods by room type/date using integer KGS values and explicit sale states.

Current Payment model and CI cover manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Current finance is operational payment control, not statutory accounting.

A complete canonical Folio/Charge/Adjustment/Void/Refund domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 7. Authentication / RBAC / property boundary

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

## 8. Operations / Staff PWA

STATUS: **VERIFIED IN CURRENT CI CONTOUR; REAL-DEVICE ACCEPTANCE OPEN.**

Current `OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Verified safeguards include assignment/claim rules, controlled task transitions, housekeeping inspection, TECH_BLOCK protection, maintenance -> DIRTY/housekeeping behavior and audit history.

Integration Staff PWA V2 includes mobile `Моя смена`, housekeeping checklist/report and technician completion reporting.

Automated/container verification does not replace real iPhone/Android/Telegram Mini App acceptance.

---

## 9. CRM / omnichannel / AI

STATUS: **PARTIAL.**

Current approved Three Crowns channel boundary:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets is a mirror/control surface, not hotel source of truth.

Core contains property-scoped conversation/message models and protected automation contracts.

AI Sales is manager-review draft assistance only:
- OWNER/MANAGER access;
- Core facts loaded server-side;
- guest conversation treated as untrusted content;
- no auto-send;
- no payment/reservation confirmation authority;
- output stored as INTERNAL `AI_DRAFT`;
- AuditLog evidence.

A universal AI Operations Administrator controlled-tool layer is not yet implemented.

Live production provider credentials/delivery remain unverified.

---

## 10. Public site / CMS / analytics

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
- repository-local property media baseline.

The production-like staging gate exposed and then verified the missing CMS migration. Public/CMS smoke now succeeds after clean `migrate deploy`.

The existing Vercel project `three-crowns-v3-preview` is only a simple preview/stub and is **not** accepted as Resort OS staging evidence.

---

## 11. Dashboard / analytics

STATUS: **IMPLEMENTED + CI-COVERED; NOT PRODUCTION-VERIFIED.**

Current management reporting includes occupancy/room nights, management ADR/RevPAR, received payments/current debtors, arrivals/departures, CRM funnel/channels, 12-category performance and operations metrics.

Management allocation metrics are explicitly not represented as statutory accounting/revenue-recognition truth.

---

## 12. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository.

The active application composition intentionally excludes NFC routers.

The full staging gate directly verifies that active OpenAPI exposes no NFC/beach HTTP routes.

Reactivation requires explicit owner decision.

---

## 13. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

Google Drive contains the fail-closed production register:
`НОМЕРНОЙ ФОНД — Три Короны — Production Import 84`.

`OWNER_CHECKLIST` still contains unresolved factual questions about specific buildings/floors, mansard rooms, cottages and several room groups. Those facts must not be guessed.

`scripts/import_physical_rooms.py` remains dry-run/fail-closed and requires exactly 84 owner-confirmed room rows before production reconciliation.

Therefore development 84/12 data is not yet owner-approved physical production truth.

---

## 14. Deployment state

### CI-local staging

STATUS: **VERIFIED.**

A complete isolated Docker topology for PostgreSQL/Core/web/admin/staff has been built, started and passed the complete staging acceptance on clean migrations with synthetic data.

### External HTTPS/WSS staging

STATUS: **BLOCKED / NOT VERIFIED.**

No connected suitable container/VPS host is currently available through the project tooling. The connected Vercel preview does not represent the required PostgreSQL + persistent FastAPI + WebSocket + multi-app staging topology.

Do not substitute the Vercel stub for external staging evidence.

### Production

STATUS: **NOT PRODUCTION READY.**

Remaining production blockers:
1. owner-confirmed physical 84-room register;
2. isolated external HTTPS/WSS staging for PostgreSQL/Core/web/admin/staff;
3. complete gate against that deployed external staging;
4. real iPhone/Android/Telegram acceptance;
5. fresh production backup/restore proof immediately before cutover;
6. production secrets, DNS cutover and documented rollback point.

No CI result alone authorizes production DNS cutover.

---

## 15. High-priority target/current gaps

### P0 / production blockers
- external HTTPS/WSS staging environment and acceptance;
- owner physical 84-room confirmation;
- real-device mobile/Telegram acceptance;
- final production backup/preflight/secrets/DNS/rollback evidence.

### P1 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- full Folio/Charge financial domain;
- complete AI Administrator controlled-tool/risk model.

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

## 16. Foundations that should be extended, not rewritten without evidence

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
- dormant NFC isolation.

---

## 17. Next release task

NEXT TASK: **Provision a real external isolated HTTPS/WSS staging host capable of running PostgreSQL + persistent FastAPI/WebSocket + web/admin/staff containers, then execute the same full gate there.**

Why this is next:
- CI-local Docker topology is now verified;
- migration/backup/restore chains are verified;
- the remaining highest-risk unknown is real network/TLS/cookie/CORS/WebSocket/mobile behavior;
- adding unrelated product features before external staging would increase code surface without reducing launch risk.

Owner involvement should be limited to factual room-register confirmations and, when infrastructure is ready, real-device acceptance; technical staging execution remains an engineering task.

LAST AUDITED: 2026-08-28
