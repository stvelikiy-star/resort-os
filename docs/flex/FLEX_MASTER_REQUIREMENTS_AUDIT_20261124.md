# MARINA SMART FLEX — verified functionality matrix and phased delivery
Date: 2026-11-24. Status: **QA ONLY / NO-GO**. Source of requirements: user master assignment, 2026-11-24. This document is evidence-based and does not approve deployment.

## Audit evidence
- Draft PR #591, head `6b7cd1f1db1dc28b6758db97b4618a7ff7627d00`, 14/14 FLEX workflows PASS. Historical `Release RC Truth CI` FAIL; do not disable. Draft PR #588 at `c849fab1708414148cee9804b581b766be71e2a1` and #590 at `5de823e48d494a7a3c4c3a3ed2145555bb5e9ba3` remain separate Draft PRs. No merge.
- Existing Console Preview `marina-smart-flex-lis3ljo6o-ai-prof-kg.vercel.app`: HTTP 200 /api/status, `configured:true`, `identity_ready:true`, `password_login:true`, `qa_onboarding_enabled:false`, `qa_linking_enabled:false`, `qa_catalog_admin_enabled:false`, `payments_enabled:false`, `payouts_enabled:false`. **This URL is not proof of a real admin login or enabled mutations.**
- Existing API Preview `marina-smart-flex-api-qakvljsfq-ai-prof-kg.vercel.app`: /health HTTP 200, `mode:QA_MANAGEMENT_READ_ONLY`, `onboarding_enabled:false`, `catalog_drafts_enabled:false`, payment/payout OFF.
- Neon `frosty-art-51219188`, database `flex_qa`, inspection READ ONLY: 43 BASE TABLEs in `flex_private` and `flex_auth`, not public. `flex_private`: hotels=0, members=1, agents=0, investors=0, subscriptions=0, skus=0, configuration_drafts=0, confirmed_payments=0. No synthetic QA data inserted.
- Repository contains SQL preview migrations 0001–0011, 13 `services/api/app/flex_*.py` modules, routes for hotel read, catalog, onboarding, drafts, partner statements, and Console. Integrated disposable PostgreSQL 16 + RLS/restore jobs are green, but are **not** validation of production recovery.
- The exact `docs/flex/FLEX_RECONCILIATION_CODEX.md` source of six earlier GET contract shapes was not found at the designated base or current branch. Never invent schemas from its name.

## Feature matrix
Classification: CODE READY = implemented and automated-contract-tested; PARTIAL = code exists but integration/operation/acceptance missing; ABSENT = required implementation not found; FROZEN = explicitly out of first release.

| Domain | Evidence / present implementation | Grade | Next acceptance |
|---|---|---|---|
| SUPER_ADMIN dashboard | `apps/flex-console/public/app.js` overview, hotels, catalog, partner summary; API reads | PARTIAL | Real isolated admin session, accurate KPIs and error/empty states |
| Hotel registry | GET /v1/hotels; POST /v1/onboarding/hotels; PENDING + idempotency/RLS SQL | PARTIAL | Admin creates and sees QA hotel, 409 altered replay, audit entry |
| Hotel-to-PMS verification | trusted deployment + Ed25519 challenge (0005), verified link | PARTIAL | Own-side PMS signer + verified tenant, revoked/expired/replay negative tests |
| Catalog SKU | GET /v1/catalog, admin GET and POST creates PLANNED; immutable capability key | PARTIAL | Enable isolated QA admin & observe persistent PLANNED, no automatic release |
| Price history | Future price versions and SQL guards; read GET versions | PARTIAL | Manual QA v1/v2, never rewrite existing paid basis |
| Tariff constructor | Configuration DRAFT/OFF and proposals | PARTIAL | Explicit BASE/BUSINESS/PREMIUM/custom package presets, discounts, trial and contracting not complete |
| Commercial hotel card | Current detail: subscription, invoices, draft history, link action | PARTIAL | Tabbed overview/modules/finances/usage/partners/history; verified data provenance |
| HOTEL_OWNER | Scoped subscription/invoices/catalog read | PARTIAL | Two isolated tenant checks, mobile/manual QA |
| SALES_AGENT | Scoped personal earnings GET; RLS | PARTIAL | Assigned hotel portfolio, conversions, payout-history contract not finished |
| INVESTOR | Scoped earnings GET with QA-only cash, RLS | PARTIAL | Contract, contribution, percent, actual cash paid, remaining obligation, end date not finished |
| PARTNER separate role | No dedicated PARTNER route/panel or role listed in Console nav | ABSENT | Contract-specific role/tenant grants; never alias SALES_AGENT/INVESTOR implicitly |
| Usage analytics | No FLEX usage-event ingestion/aggregation/storage endpoint or telemetry event schema found in current isolated FLEX modules and 0001–0011 | ABSENT | Shared versioned contract, idempotent aggregate-only ingestion, bounded retention, UI |
| Entitlement dispatch | Commercial entitlement pure helpers; no verified PMS apply/ack path | PARTIAL | Signed revisioned outbox + receipt, RBAC independent, no direct PMS write |
| Payment, bank, QR, refunds, payouts | Preview schemas and isolated code/contract tests, no live provider | FROZEN | Separate financial/legal acceptance; feature flags OFF |
| True SUPER ADMIN and role access | Better Auth preview identity, role/JWT server checks; one member in QA | PARTIAL | Legitimate password recovery, authorized role sessions, no browser role override |
| RU/KG/EN, Desktop/Mobile | Console translations/tests, designs | PARTIAL | Browser screenshot acceptance 320/390/desktop + dark/light |
| Backup + recovery | Disposable PG16 restore workflow | PARTIAL | Independent backup recovery of the selected QA/prod candidate |

## Existing contract boundaries, not to duplicate
- Hotel staff, bookings, folio, restaurant, kitchen, warehouse, staff RBAC stay exclusively in MARINA SMART.
- FLEX owns commercial customer, tariff/version/contract/subscription/ledger/partner records. A FLEX capability grant never grants employee permissions.
- Never join PMS operational DB for mutations; no guest PII, password, tokens, message bodies or documents in analytics.
- Do not create per-hotel projects, new DNS/Cloudflare tokens, or force MFA enrollment merely to test read-only QA. Existing staging role checks remain fail-closed; simplifying user flow is separate from bypassing authorization.

## Proposed hotel card information architecture (DESIGN, not delivered UI)
1. Overview — commercial ID, verified linkage, onboarding state, assigned agent, current agreement; missing values shown as unavailable rather than zero.
2. Subscription & modules — base plan, explicit SKU grants, available add-ons, dated **proposed** changes, pricing snapshots, active entitlement revision; payment/activation unavailable in initial QA.
3. Finance — billed, confirmed paid, reversals, due, net, actual disbursements **distinct**; no fabricated cash.
4. Usage — day/week/month aggregates of clicks versus successful operations, capability, platform and result; initially "data source not connected."
5. Commercial relationships — agent attribution, partner/investor relationships only for authorized roles, confidential terms separately scoped.
6. Audit history — append-only actor/time/change-version and provenance, no secret material.
Filters and exports use server-scoped reads and RLS. Mobile tabs adapt to 320/390 px.

## Proposed paid-module lifecycle (DESIGN)
`PLANNED -> VERIFIED TECHNICAL CAPABILITY -> AVAILABLE -> OFFERED IN DRAFT -> AGREED -> (after payment gate approval) AUTHORIZED ENTITLEMENT`. Current QA allows only PLANNED/pricing/DRAFT/OFF. Discount, trial, bundle, price version and effective dates attach to immutable commercial snapshots; a later catalog price must not retroactively alter agreed amounts. Disabled module keeps historical hotel data. The live entitlement stage is deliberately not implemented here.

## Minimum safe first release and implementation order
**Release candidate 1 (management QA, not bank launch):** verified isolated admin; PENDING hotel creation; trusted-link QA; complete catalog read and PLANNED creation; future-price history; DRAFT/OFF subscriptions; HOTEL_OWNER read; SALES_AGENT and INVESTOR QA-only personal earnings; five-role isolation plan including PARTNER (if implemented and accepted); RU/KG/EN, dark/light/mobile; backups; a single accepted SHA. No real invoice issuance, bank collection, QR, payments, refunds, payouts, or PMS ENFORCE.

Priority steps:
1. Complete and review `MARINA_SMART_FLEX_INTEGRATION_CONTRACT.md` as **PROPOSAL**, hand off PMS-only tasks to its maintainer.
2. Implement tabbed commercial hotel card against existing GETs with honest "not connected" states for unavailable sources. Do not fabricate financial fields.
3. Complete tariff-constructor commercial draft workflow (no activation) using existing catalog and SQL; add real end-to-end disposable PostgreSQL/HTTP tests.
4. Define isolated usage-event schema and retention, add ingest only after signed origin and tenant mapping reviewed.
5. Add PARTNER role as distinct access scope only after contract-specific data model and negative RLS acceptance.
6. Add contract visibility and payment-separated statements to AGENT/INVESTOR using verified sources, not synthetic public values.
7. Publish one Preview when the free Vercel deployment capacity allows; manual UX and production gates afterwards.

## Current blockers
- Live authorized administration in connected QA is not accepted; one platform membership and no test hotel or catalog.
- Old main Release RC Truth FAIL remains independent.
- Vercel API returned 402 `api-deployments-free-per-day` during the last preview attempt; no paid upgrade or alternative project authorized.
- Full PMS contract requires approval from separate MARINA SMART maintainer; no current telemetry source or entitlement write channel.
- Entire first financial phase FROZEN; new source has broader long-term aspirations that do not override freeze.

**NO-GO:** No production, live PMS feature toggles, or financial activation.