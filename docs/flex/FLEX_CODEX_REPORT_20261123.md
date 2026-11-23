# MARINA SMART FLEX — CODEX audit / 2026-11-23

> **NO-GO.** Only isolated FLEX QA and local/disposable checks. No real PMS, production, Docker, existing DB, bank, paid invoices, QR, payouts, ENFORCE, or main modifications.

## Branch and provenance

- Repository: `stvelikiy-star/resort-os`.
- **Requested base**: `b0f99f300a93356b379fa0f607157722f95636a5` (not the advanced head of #588).
- **Exclusive work branch**: `feat/marina-flex-fixes-20261123`.
- Draft PR: [#591](https://github.com/stvelikiy-star/resort-os/pull/591), target `main`, **do not merge**.
- First fix commit: `2a3dcb2482290fd7dad9398854a96b564725a911`.
- #588 source branch had advanced by **two commits** since `b0f99f30`; HEAD `c849fab1708414148cee9804b581b766be71e2a1`. Those two commits were **not imported or silently cherry-picked**.
- Frozen user decision 23.11.2026: payment/QR/issued invoices/payouts/automatic hotel blocking deferred; `payments_enabled=false`, `payouts_enabled=false`, `ENFORCE` must remain OFF. Future payment method cash, **not implemented**.

## Files changed (commit 2a3dcb)

| File | What changed |
| --- | --- |
| `apps/flex-console/package-lock.json` | Generated npm lockfile v3; `better-auth@1.7.27`, `pg@8.16.3`. |
| `apps/flex-console/public/styles.css` | MARINA Future Luxury 2.0 dark/light tokens, 44 px controls, focus #14b8a6, 390/820 layouts; no business logic. |
| `apps/flex-console/public/index.html` | Existing MARINA logo, visible QA/DEMO and localized Frozen notice; no new actions. |
| `apps/flex-console/public/app.js` | RU/KG/EN label for Frozen banner; all role behavior unchanged. |
| `apps/flex-console/public/marina-smart-logo.webp` | Byte-for-byte copy from `apps/admin/public/marina-smart-logo.webp`; admin untouched. |
| `.github/workflows/marina-flex-console-ci.yml` | `npm ci` and explicit `NODE_ENV=test node --test apps/flex-console/test/*.test.mjs` in CI. |
| `services/api/requirements-flex-control.txt` | Isolated pinned FastAPI 0.136.3, HTTPX 0.28.1, asyncpg 0.30.0, Pydantic 2.11.7, PyJWT 2.10.1. |
| `scripts/marina_flex_release_scope_guard.py` | Explicitly allows only two new FLEX files: lockfile and logo; still denies PMS paths, non-additive changes and symlinks. |

## Command evidence — local isolated repo clone (no live DB)

| Command/check | Result |
| --- | --- |
| `git rev-parse HEAD` after cloning requested fix branch | `b0f99f300a93356b379fa0f607157722f95636a5` before edits |
| `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` (FLEX directory) | PASS, lockfile v3, pinned versions verified |
| `npm ci --ignore-scripts --no-audit --no-fund` (FLEX directory) | **PASS** |
| `NODE_ENV=test node --test test/*.test.mjs` (FLEX directory) | **19 tests, 19 PASS, 0 FAIL, 0 skipped** |
| `python3 scripts/marina_flex_release_scope_guard.py --self-test` | **PASS** |
| `node --check apps/flex-console/public/app.js` | **PASS** |
| GitHub [FLEX Console CI](https://github.com/stvelikiy-star/resort-os/actions/runs/45223280988) on `2a3dcb` | **PASS** |
| GitHub [FLEX Integrated QA Restore and Scope](https://github.com/stvelikiy-star/resort-os/actions/runs/45223280756) on `2a3dcb` | **PASS**, two jobs: scope/domain and isolated PG16 install/restore |
| GitHub specialized FLEX workflows on `2a3dcb` | **14/14 PASS** |
| GitHub historical `Release RC Truth CI` | **FAIL** (separate November/main gate; **not bypassed**) |

`*_http_test.py` is restricted to GitHub Actions jobs with **disposable PostgreSQL 16 service containers**, not the existing Neon QA or PMS. The integration workflow runs the **0001–0011** SQL migrations on an empty `flex_ci` DB, synthetic RLS cases and independent backup/restore. These are **CI evidence**, not evidence of a cloud staging rollout.

### Gate 0–10 — sequential acceptance

PASS means that the **complete gate** has evidence, not just one unit test. **FAIL** includes missing or unverified mandatory evidence.

| Gate | Status | Evidence / exact blocker |
| --- | --- | --- |
| **0** PR SHA and checks | **FAIL / NO-GO** | #588 currently `c849fab1` (its own 37/37 PR checks PASS), but requested fork is `b0f99f30`, missing two later commits. New #591 has 14/14 FLEX checks PASS but historical `Release RC Truth CI` FAIL. No merged/common release candidate. |
| **1** PG16 / migrations / RLS / restore | **PASS (disposable CI only)** | `MARINA FLEX Integrated QA Restore and Scope` both jobs PASS: isolated PG16, 0001–0011, RLS/synthetic hotels and independent restore. No existing DB accessed. |
| **2** Vercel QA + Cloudflare DNS/TLS/Access | **FAIL** | No new-branch QA deployment, Cloudflare Access/TLS routing and private origins verification for this exact SHA. Existing Vercel previews for other SHA do not count. |
| **3** OIDC EdDSA/MFA staging | **FAIL** | Auth/MFA package imports pass 19/19 tests, but real issuer + TOTP + session + roles on isolated staging not authenticated end-to-end. |
| **4** SUPER_ADMIN PENDING registration | **FAIL** | Disposable signed onboarding contract checks exist; no live staging create/replay/409/403 trace for this branch. |
| **5** HOTEL_OWNER cross-hotel isolation | **FAIL** | RLS synthetic cases passed in disposable CI; signed HTTP Hotel A/B negative cases on this SHA not proven in staging. |
| **6** Planned catalog / price versions / DRAFT OFF | **FAIL** | Catalog synthetic CI PASS; no accepted staging version/draft row diff on this SHA. No finance writes permitted. |
| **7** SALES_AGENT / INVESTOR A/B | **FAIL** | Partner earnings unit/SQL contracts PASS; live separate-role login and isolation evidence absent. Actual payouts permanently frozen for this release. |
| **8** Browser + 390/820/1440 + RU/KG/EN | **FAIL** | Styling changes committed; screenshot/accessibility/readability and real authenticated role flows require browser evidence. A QA/DEMO mock screenshot is not staging E2E proof. |
| **9** Payment/payout/ENFORCE freeze | **FAIL (strict gate)** | Code and CI preserve frozen financial behavior; independent `/api/status` verification for newly deployed #591 and rejection of all forbidden POST routes pending. |
| **10** Unified release / off-site backup / rollback | **FAIL** | No signed staging acceptance, Cloudflare boundary verification, production-free rollback drill or 5xx monitoring evidence for #591. |

**Final status: NO-GO.** No gate was silently skipped, and a CI PASS is not counted as live staging E2E.

## D. Six GET reconciliation API contracts — source missing

`docs/flex/FLEX_RECONCILIATION_CODEX.md` **does not exist** in the specified base SHA, current source branch of #588, main, or the inspected FLEX UI branch. Project file search also returned no copy. The exact six contract specifications are therefore **unavailable**. Do **not** invent schemas, response fields or financial data, and do not substitute payment functionality. D remains **BLOCKED / FAIL** pending the genuine contract document. Existing protected GET routes are preserved; no POST, bank, QR or payout routes were added.

## E. Draft PR dependency stack — do not merge into main

Exact discovered PR graph:

| PR | Subject / dependent base |
| --- | --- |
| **#574** | Commercial foundation; base `main`. |
| **#575** | Read-only control plane / RLS; base branch of #574. |
| **#576** | Catalog pricing; base branch of #575. |
| **#577** | PENDING hotel onboarding; base branch of #576. |
| **#578** | Subscription core; base branch of #577. |
| **#579** | Invoice / ledger **contracts only**, base #578; issuance frozen. |
| **#580** | Refund reconciliation **contracts only**, base #579; refunds frozen. |
| **#581** | QR provider boundary **documentation/contract only**, base #580; QR integration frozen. |
| **#582** | Signed synthetic settlement QA only, base #581; no real receipts. |
| **#583** | Renewal proposal / guard only, base #582; never enable ENFORCE. |
| **#584** | Agent/investor earnings QA, base #583; actual payouts frozen. |
| **#588** | PLANNED catalog, future pricing and OFF drafts; base `feat/marina-flex-p0-hotel-link-admin-20261123`, **not directly #584**. |
| **#591** | This review branch, exact fork `b0f99f30`, draft to main; no merge. |

**Recommended order:** keep #574→#584 in original dependency order; first compare the intermediate #585–587 ancestry and the two commits after `b0f99f30` in #588. Only after precise file/commit equivalence and release-scope guard confirmation decide what to consolidate in a single fresh candidate. **Do not close any Draft PR** merely due to duplicate title; close redundant PRs only after unique changes are proven carried forward. No direct merge of frozen finance/QR/ENFORCE code.

## Open risks and next actions

1. **P0** Obtain the genuine `FLEX_RECONCILIATION_CODEX.md` and implement its six **GET-only** contracts with isolated tests; no invented API.
2. **P0** Reconcile the difference between `b0f99f30` and current #588 HEAD without silently moving the requested branch base.
3. **P0** Keep PR #591 Draft; inspect historical red check separately, without changing `main` or November release.
4. **P0** On an isolated non-production Vercel preview for the exact SHA, prove health/status, encrypted auth, signed MFA and cross-tenant E2E, preserving disabled finance and enforcement.
5. **P0** Read-only Cloudflare DNS/TLS/Access audit for FLEX preview; no changes to PMS domains.
6. **P1** Capture role-by-role 1440/390 visual evidence and keyboard/color/language checks using QA/DEMO data. Never claim a mock screenshot is a successful real user login.
7. **P1** Review the dependent Draft PR stack; close only after verified code inclusion and deliberate owner approval.

**Explicit freeze:** `payments_enabled=false`; `payouts_enabled=false`; invoices to pay, QR payments, agent/investor payouts and automatic `ENFORCE` remain disabled. Cash is a future option, **not developed here**.

## Update — verified #588 delta after requested base (2026-11-23)

Read-only Git comparison `b0f99f300a93356b379fa0f607157722f95636a5...c849fab1708414148cee9804b581b766be71e2a1` returned **2 commits, 11 modified files, +75/-26 lines**. The exact differences are **not yet included in #591**; both branches now diverge. The added changes concern:

- `apps/flex-console/auth/identity-enabled.mjs`, `mfa-bridge.mjs`: QA-preview-only `FLEX_QA_PASSWORD_LOGIN` mode, password-authenticated session signing; production/TOTP behavior remains distinct. Copying these requires specific negative JWT/session tests and browser E2E evidence.
- `apps/flex-console/server.mjs`: QA-origin-only Vercel protection bypass header for API service-to-service GETs, plus session and status plumbing. Requires origin/secret constraints to be rechecked, without exposing the secret.
- `services/api/app/flex_control_plane.py` and bundled `apps/flex-api-qa/app/flex_control_plane.py`: password-only **read** permission in QA Preview, signed JWT `amr=['pwd']` constraint, no role claims taken from the user.
- `services/api/app/flex_partner_portal.py` and bundled copy: corresponding restricted QA read-only checks for investor/admin.
- `apps/flex-console/public/app.js`, `enroll.html`, `enroll.js`: UI behavior and enrollment text changes.
- `apps/flex-console/test/first-login-postgres.mjs`: +22 lines of password login regression assertions.

**Decision:** Do not silently claim parity or close #588. Before consolidation, review each hunk and preserve the original #591 base and frozen payment/ENFORCE conditions. This delta is an unmerged dependency and remains a Gate 0 blocker.

**Gate 0 verification refinement:** #588's own HEAD reports 37/37 GitHub workflow checks SUCCESS; that proves its own commit, **not** the two-branch combined candidate. The #591 HEAD includes a separate red historical `Release RC Truth CI` unrelated to FLEX. Current #591 14/14 FLEX CI tests PASS; Gate 0 remains NO-GO because no single verified combined candidate has passed scope and security acceptance.

**GET contract specification search:** GitHub base SHA, HEAD #588, main, latest checked FLEX UI branch and Project file search contain no `docs/flex/FLEX_RECONCILIATION_CODEX.md`. Its exact six response schemas are not known. No substitute payment-related routes have been invented.

## Supplementary reference discovery — Library API map (not a substitute for D)

A personal Library document named `MARINA_FLEX_UI_Backend_Integration_Map.md` dated 2026-11-22 was located. It lists existing isolated routes (`GET /v1/me`, `/v1/hotels`, `/v1/hotels/{id}/subscription`, `/v1/hotels/{id}/invoices`, `/v1/catalog`, partner earnings, admin summary), but **does not define the six exact new reconciliation contracts**, their response schemas, or verification assertions. The requested `FLEX_RECONCILIATION_CODEX.md` remains missing. This partial discovery does not authorize inventing the six contracts. Gate D = BLOCKED / FAIL.
