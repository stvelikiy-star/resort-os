# RESORT OS — CURRENT STATE

Version: 1.7
Date: 2026-08-28
Status: EVIDENCE-BASED INTEGRATION RELEASE CANDIDATE / NOT PRODUCTION CUTOVER READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: factual implementation reality only

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. DEVELOPMENT/CI VERIFIED != PRODUCTION VERIFIED.**

This document describes the current integration candidate on branch `integration/site-pms-cms-20260827` and its verified evidence. It does not redefine Product Bible, Domain Business Rules, target architecture or AI governance.

---

## 1. Audited baseline

Repository: `stvelikiy-star/resort-os`.

Audited integration head: `db2ba85466c985cecfe0c1fb08bbc29d33a990c4`.

Open integration PR: `#37 — Unify site, V9 PMS/CRM, analytics, staff and staging through Resort Core`.

PR state at audit time:
- OPEN;
- not merged;
- mergeable;
- current integration branch remains separate from canonical `main`.

Current physical/runtime architecture evidenced in repository:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical application entrypoint: `services/api/app/app_entry.py` -> `app.app_entry:app`.

Integration app version is set to `0.34.0` in the composition layer.

Repository shape:
- `apps/web` — public Next.js web;
- `apps/admin` — PMS/admin Next.js;
- `apps/staff` — staff Next.js/PWA;
- `services/api` — FastAPI Resort Core;
- `packages/database` — Prisma/PostgreSQL schema, SQL constraints, migration baseline;
- `automation/n8n` — workflow definitions/runbooks;
- `scripts` — seed, migration, backup/restore, release/staging checks;
- `knowledge` / `docs` — canonical and implementation documentation.

---

## 2. Verification evidence on audited head

GitHub Actions for commit `db2ba85466c985cecfe0c1fb08bbc29d33a990c4` completed with `success` for the active repository matrix, including:
- Resort Core CI;
- PMS Chessboard Mutation CI;
- Hotel Operations CI;
- Realtime PMS CI;
- Payment Idempotency CI;
- Production Migration Baseline CI;
- PostgreSQL Backup Restore CI;
- Public Site Truth CI;
- Control Center Monorepo Contract CI;
- Data Intake Integrity CI;
- Staff Voice CI;
- Telegram Sales CI;
- AI Sales Draft CI;
- Unified Inbox CI;
- n8n Resort Core Contract CI;
- Automation Contract CI;
- NFC Deferred Scope CI.

Important correction to previous transient CI blocker: on this audited head, workflow jobs contain actual executed step lists. `steps=null` is NOT the state of the audited head.

Representative verified Core CI steps include:
- admin/web/staff typecheck + production build;
- Core install/compile/start;
- schema + constraints + Three Crowns seed;
- public availability + ReservationRequest creation;
- protected PMS authentication;
- unified Site/CMS/CRM/PMS smoke;
- manager quote without global automatic prepayment rule;
- manager-recorded payment -> atomic Reservation creation;
- payment idempotency;
- Reservation visibility in PMS;
- check-in -> checkout -> housekeeping lifecycle.

Representative verified Chessboard CI steps include:
- schedule read;
- preview and atomic whole-reservation move;
- stale-snapshot rejection;
- resize and Split Stay across two rooms;
- CLEAN-room requirement for check-in;
- immediate relocation preserving lived history;
- vacated-room dirtying;
- conflict rollback;
- schedule-aware checkout;
- AuditLog evidence.

Production-like migration and backup/restore workflows also execute real steps on clean PostgreSQL containers, including Prisma migration history and critical database constraints.

These are CI/development environment proofs, not production runtime proofs.

---

## 3. Canonical Three Crowns V1 business boundary

STATUS: VERIFIED IN CURRENT CI-COVERED FLOW.

Active property-specific rule:
- `ReservationRequest != Reservation`;
- final Reservation confirmation requires manager/human action;
- an unpaid request does not hold inventory;
- manager chooses prepayment amount/terms/method;
- manager collects payment manually;
- Resort OS records manager-confirmed payment facts;
- no active global `PREPAYMENT_PERCENT` is authoritative;
- n8n/AI cannot directly create a guaranteed Reservation, confirm payment, check-in/out/refund or mutate hotel money.

Public request endpoint creates `ReservationRequest` and explicitly returns `is_reservation: false`.

Manager conversion is the controlled path to Reservation + InventoryBlock + Payment.

---

## 4. PMS / Smart Booking Board

STATUS: VERIFIED DEVELOPMENT/CI BASELINE ON INTEGRATION HEAD.

Primary production admin surface includes PMS V9 UI while mutation authority remains server-side.

Server-authoritative schedule contract retains read -> preview -> explicit commit semantics.

Verified behavior includes:
- visual reservation spans;
- room/date drag movement;
- date resize;
- full move;
- Split Stay / segmented room assignment through multiple Reservation inventory blocks;
- partial relocation from an effective date;
- stale-version rejection;
- conflict preview/rollback;
- PostgreSQL exclusion constraint as final active-overlap guard;
- TECH_BLOCK safety;
- CLEAN requirement for immediate destination room;
- vacated room -> DIRTY plus housekeeping creation/reuse;
- server-side pricing impact preview;
- explicit manager confirmation before commit;
- AuditLog evidence;
- realtime PMS snapshot contract.

PMS V9 adds control snapshot and safe bulk task operations in the integration branch. Their code is composed into Resort Core and covered by the current integrated CI contour, but external production usage is not yet proven.

---

## 5. Availability / inventory / concurrency

STATUS: VERIFIED FOR CURRENT ROOM-level Three Crowns MODEL IN CI.

Current model uses physical `Room` inventory plus `InventoryBlock` date ranges.

Database invariant:
- active `InventoryBlock` rows for the same room cannot overlap because PostgreSQL uses a GiST exclusion constraint over `[startDate,endDate)`.

Current availability query:
- excludes `TECH_BLOCK` rooms;
- checks active overlapping room blocks;
- uses half-open date interval semantics `[)`;
- reads pricing from server-side rate periods.

Concurrency protections for schedule mutation and payment idempotency are exercised by dedicated CI contracts.

Generic Resort OS room-type inventory/overbooking/external channel inventory rules remain product/domain decisions and are not promoted from this property-specific implementation.

---

## 6. Pricing

STATUS: PARTIAL / VERIFIED FOR CURRENT THREE CROWNS RATE-PERIOD BASELINE.

Current deterministic server pricing exists in Resort Core:
- rate plan + room type + date periods;
- integer KGS prices;
- OPEN/CLOSED/CONFIRM_REQUIRED sale states;
- nightly calculation;
- missing-rate failure;
- server-side schedule-change price delta preview.

Current implementation does NOT prove a generic Resort OS pricing engine for:
- child-age rules;
- extra bed;
- meal-plan calculation beyond stored label;
- promo/discount/corporate/partner rules;
- tax/fee rules;
- multi-currency conversion;
- generic Split Stay repricing policy.

Those remain governed by canonical DECISION REQUIRED / VALIDATE rules.

---

## 7. Guest / Reservation / Stay domain model

STATUS: PARTIAL.

Verified separate persisted concepts:
- `Guest`;
- `ReservationRequest`;
- `Reservation`;
- `InventoryBlock` room/date segments.

Current implementation does NOT contain a distinct persisted canonical `Stay` entity in the audited Prisma schema.

Operational stay lifecycle is currently represented largely through `Reservation.status` (`GUARANTEED`, `CHECKED_IN`, `CHECKED_OUT`, etc.) plus segmented InventoryBlocks.

Therefore:
- Guest != Reservation is implemented;
- ReservationRequest != Reservation is implemented;
- Split Stay behavior is implemented through segmented inventory assignment;
- canonical `Guest != Reservation != Stay` data-model separation is NOT fully implemented.

This is a target/current architectural GAP. It is not, by itself, evidence that current Three Crowns V1 flows are broken. Any migration to a distinct Stay aggregate must be designed from approved business rules and migration impact rather than performed as an automatic rewrite.

---

## 8. Finance / payments

STATUS: PARTIAL; MANAGER-MANUAL PAYMENT CONTROL VERIFIED.

Implemented persisted `Payment` facts include:
- positive integer KGS amount;
- status;
- method;
- provider/reference fields;
- request/reservation context;
- globally unique idempotency key;
- `(provider, externalRef)` uniqueness.

Dedicated CI verifies idempotency and manager payment conversion behavior.

Current finance is operational payment control, not a full accounting/folio system.

No canonical persisted Folio/Charge/Adjustment/Void aggregate is implemented in the audited schema.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 9. Authentication / authorization / property isolation

STATUS: VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE-BASED CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.

Current staff auth evidence:
- Argon2 password hashing;
- random session token stored only as SHA-256 hash;
- HttpOnly cookie;
- session expiry/revocation;
- inactive-user rejection;
- server-side `require_roles(...)` dependencies;
- audit on login;
- user bound to a Property.

Current runtime is explicitly property-selected by environment `PROPERTY_CODE` and rejects sessions whose property code differs from the active property.

This is a useful fail-closed Three Crowns boundary, but it is NOT a generic multi-tenant architecture proof.

Current gaps/risks:
- generic Organization/Tenant hierarchy not implemented;
- cross-property workflows/reports not implemented;
- resource-level permission model remains narrower than target universal RBAC;
- explicit application-level login rate limiting is not evidenced in `auth.py`;
- production cookie/TLS settings depend on environment and therefore require deployed staging/production verification.

---

## 10. Operations / housekeeping / maintenance

STATUS: VERIFIED FOR ACTIVE THREE CROWNS FLOW.

Implemented reusable `OperationalTask` covers:
- HOUSEKEEPING;
- MAINTENANCE;
- GUEST_REQUEST.

Current task states:
`OPEN -> IN_PROGRESS -> IN_INSPECTION -> DONE`, with cancellation and manager inspection/rework controls where applicable.

Verified safeguards include:
- assignment/claim rules;
- housekeeping inspection boundary;
- TECH_BLOCK protection;
- maintenance completion -> DIRTY/housekeeping behavior;
- task transition AuditLog.

Integration branch Staff PWA V2 adds mobile `Моя смена` flow, housekeeping checklist/report and technician completion reporting. Current CI succeeds on the integrated head. Real-device mobile acceptance is still required before production cutover.

---

## 11. CRM / omnichannel / AI

STATUS: PARTIAL.

Implemented communication data model includes property-scoped channels, conversations and messages.

Current active architecture decision:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets CRM is a mirror/control surface, not hotel truth.

Repository contains n8n workflow contracts and a read-only CRM feed. Repository/CI evidence does not by itself prove live production credentials/provider delivery.

AI Sales current implementation is manager-review draft assistance:
- OWNER/MANAGER only;
- loads property-scoped Core facts;
- treats guest messages as untrusted conversation data in its prompt contract;
- does not auto-send;
- does not confirm payments/reservations;
- stores AI output as INTERNAL `AI_DRAFT` message;
- records AuditLog evidence.

This is NOT the full target AI Administrator. In particular, a universal AI Operations tool layer and complete risk/approval tool matrix are not implemented.

---

## 12. Public site / CMS / analytics

STATUS: IMPLEMENTED IN INTEGRATION CANDIDATE; CI-COVERED BUILD/TRUTH CONTRACTS VERIFIED; FINAL EXTERNAL VISUAL/MEDIA ACCEPTANCE OPEN.

Current public web includes:
- premium Three Crowns site;
- 12-category room catalog/pages;
- Core-backed availability/pricing;
- ReservationRequest submission;
- explicit request-not-booking boundary;
- multilingual RU/KG/EN integration branch work;
- CMS content runtime with Resort Core boundary;
- privacy-safe vendor-neutral booking funnel events;
- metadata/SEO routes;
- repository-local property media baseline.

Public Site Truth CI succeeds on audited head.

Production public acceptance remains dependent on external staging/mobile/media review.

---

## 13. Analytics / Command Center

STATUS: IMPLEMENTED + CI-COVERED ON INTEGRATION CANDIDATE; NOT PRODUCTION-VERIFIED.

Integration branch adds `GET /api/v1/admin/reports/overview` and admin report UI covering management metrics such as:
- occupancy / room nights;
- management ADR / RevPAR;
- received payments and current debtors;
- arrivals / departures;
- CRM funnel and channels;
- 12-category performance;
- operations.

Accounting truth is explicitly separated from management allocation metrics.

No claim of statutory accounting/revenue recognition is made.

---

## 14. Services / resources / partners / guest portal

STATUS: NOT IMPLEMENTED AS GENERIC TARGET DOMAINS / UNKNOWN WHERE NO EXECUTABLE DOMAIN EXISTS.

No evidence in the audited core schema establishes complete target implementations for:
- Folio/Charge engine;
- generic Service engine;
- generic Resource/Scheduling engine;
- Partner/Agent settlement domain;
- secure Guest Portal/Stay token boundary;
- generic multi-property management.

These are target gaps and/or VALIDATE/DECISION REQUIRED areas. They are not all Three Crowns V1 launch blockers.

---

## 15. NFC

STATUS: DEFERRED / DORMANT.

Historical NFC schema/source remains in repository, including `BEACH_PARTNER`/NFC models and SQL.

`app.app_entry:app` intentionally does not compose NFC routers on the audited integration head.

NFC must not be reactivated without an explicit owner decision.

---

## 16. Database / migrations / backup-restore

STATUS: VERIFIED IN CLEAN CI ENVIRONMENT; PRODUCTION CUTOVER PROOF STILL REQUIRED.

Current integration candidate includes:
- PostgreSQL;
- Prisma schema;
- committed `prisma/migrations/0_init/migration.sql` plus SHA-256 checksum;
- clean `prisma migrate deploy` CI;
- migration history validation;
- critical PostgreSQL constraints;
- migration-aware backup artifact;
- clean restore verification;
- restored migration ledger comparison.

Critical current DB constraints include date/amount checks and the active room-overlap exclusion guard.

Production database is not yet proven by CI container evidence alone.

---

## 17. Physical Three Crowns room truth

STATUS: BLOCKED FOR PRODUCTION IMPORT / DEVELOPMENT BASELINE VERIFIED.

Development intake contains 84 room positions / 12 categories and is integrity-checked in CI.

The physical room register still contains reconstruction questions (`UNKNOWN` / explicit confirmation items). A fail-closed owner approval sheet exists in Google Drive:
`НОМЕРНОЙ ФОНД — Три Короны — Production Import 84`.

`scripts/import_physical_rooms.py` is dry-run/fail-closed and requires exactly 84 confirmed rooms before guarded production reconciliation.

Therefore 84/12 development data must not be described as owner-approved physical production truth yet.

---

## 18. Deployment / production state

STATUS: NOT PRODUCTION CUTOVER READY.

Repository contains:
- production compose/runbooks;
- staging env template;
- isolated staging compose;
- staging Caddy example;
- staging bootstrap and acceptance scripts;
- production preflight;
- backup/restore tooling.

Production cutover remains blocked by external/runtime evidence, specifically:
1. owner-confirmed physical 84-room register;
2. isolated HTTPS/WSS staging deployment for PostgreSQL/Core/web/admin/staff;
3. full `staging_full_gate.py` against deployed staging;
4. real iPhone/Android/Telegram mobile acceptance;
5. fresh production backup/restore proof immediately before cutover;
6. production secrets, DNS cutover and rollback point.

No CI result alone authorizes production merge/DNS cutover.

---

## 19. High-priority target/current gaps

### P0 / production blockers
- physical 84-room owner confirmation for production import;
- deployed HTTPS/WSS staging acceptance before cutover;
- final production backup/preflight/secrets/DNS/rollback evidence.

### P1 architecture/product gaps (not automatic rewrite mandates)
- distinct canonical Stay domain/persistence is not implemented;
- current auth/property model is single-property oriented, not generic multi-tenancy;
- full Folio/Charge financial domain is absent;
- complete AI Administrator controlled tool/risk model is absent.

### VALIDATE / DECISION REQUIRED
- generic reservation/stay lifecycle details beyond property-specific implemented baseline;
- generic pricing rules;
- Folio/refund/adjustment/void rules;
- Partner/Agent commissions/settlements;
- Service/Resource scheduling model;
- generic multi-property model;
- payment provider/acquiring strategy;
- complete AI provider/tool approval model;
- live omnichannel provider credentials and production verification.

### DEFER
- NFC / beach wallet for current Three Crowns V1.

---

## 20. Things that should be extended rather than rewritten without evidence

The following current foundations have strong implementation/CI evidence and should be preserved unless a later audit proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and overlap exclusion constraint;
- ReservationRequest -> human manager conversion boundary;
- server-authoritative PMS schedule preview/commit contract;
- payment idempotency contract;
- AuditLog pattern;
- property-scoped staff sessions/RBAC baseline;
- OperationalTask engine for housekeeping/maintenance/guest requests;
- read-only CRM mirror boundary;
- n8n as orchestration rather than DB authority;
- public site using Resort Core for availability/pricing/request creation;
- dormant NFC separation from active V1 runtime.

---

## 21. Next technical task from this audit

NEXT TASK: **Provision isolated HTTPS/WSS Three Crowns staging and execute the complete staging gate on the audited integration candidate.**

Priority: P0 production dependency.

Why first:
- current code has strong clean-CI evidence;
- production cutover is still blocked by environment/runtime verification;
- staging can expose integration/configuration/security/mobile defects that code-only CI cannot prove;
- performing a new architectural rewrite before this gate would reduce evidence quality and increase migration risk.

Required verification:
- clean staging PostgreSQL with committed migration baseline;
- Core/web/admin/staff start successfully;
- Secure cookie + exact CORS origins + HTTPS/WSS;
- `staging_full_gate.py` / staging acceptance succeeds with synthetic data;
- public booking boundary remains Request -> human confirmation;
- PMS move/split/conflict/check-in/out/housekeeping flows succeed;
- analytics/report endpoint responds with synthetic management data;
- staff MAID/TECHNICIAN lifecycle succeeds;
- no NFC routes are exposed;
- provider credentials remain staging-only;
- real mobile/Telegram acceptance follows before production cutover.

LAST AUDITED: 2026-08-28
