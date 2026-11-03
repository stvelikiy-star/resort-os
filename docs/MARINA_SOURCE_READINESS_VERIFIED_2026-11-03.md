# MARINA SMART — source readiness audit (2026-11-03)

**Scope:** Repository-only verification. This is not an approval for Ubuntu deployment, demo modification, production cutover, payments, live WhatsApp, or OTA connectivity.

**Read-only audit basis:** `stvelikiy-star/resort-os`.
- Base candidate PR #244 at `fb556606d7d2d0db8035fc1459e0fc0de7d58ac5`: 70 GitHub Actions runs on that SHA returned success. A successful workflow is not a live production test.
- P0 audit PR #272 at `75e7ab1eea7f5339c0c6bd6162a9fb2041d2b389`: 22 success and one failure (`Three Crowns Full Staging Gate`, run 41595261485, step `Validate release/data truth and seed canonical hotel`).
- HOLD integration PR #276 at `794f1d5b1e5da30bca8fa5fe4f790f4c79e09a79`: 58 success and one failure (`Beget Production Hardening CI`, run 41597940679, step `Verify public truth still blocks rejected sports/payment drift`).
- Staff mobile PR #273 at `52edc58f0e08119f03a974ccf7b7356d8bd8fdbd`: 8 success; Android debug job was in progress at query time, 2026-11-03. No signed APK or installed-device QA verified.

These branches are **separate**, and no fully accepted combined release SHA has been verified. Cross-product CI failures above are not proof of a MARINA PMS defect; do not change other properties' content to silence checks.

## Confirmed source facts

| Area | Verified fact | Remaining acceptance gate |
|---|---|---|
| Source and deployment boundaries | Dedicated MARINA demo, fleet and per-hotel production compose paths; `main` is not the verified P0 release candidate. | Reconcile exact source SHA, image digest and deployed environment before release. |
| Database migrations | `migration.sql` file counts: 38 on #244/#272/#273, 39 on #276; the additional migration is `zz114_marina_60minute_holds_20261029`. | Run exact schema/constraint verification and disposable restore/rollback against a unified candidate, then later against target host. |
| Employee creation | `staff_control.py` exposes OWNER-only POST /api/v1/admin/staff, property-scoped username lookup, password policy, INSERT and audit logging. PATCH revokes active sessions on security-related changes. | Real create → sign-in → custom grant → revoke → re-sign-in API/browser E2E has **not** been demonstrated. Do not claim the earlier creation failure is fixed. |
| Permissions | `section_permissions.py` maps 26 modules; owner retains protected staff administration. Synthetic permission tests exist. | Every role's allowed/denied server requests; cross-property ID denial; revocation effects. |
| Shared platform | `shared_auth_preview.py` allows only login/logout/me/mode and health in opt-in isolated staging; all other HTTP/WS routes are closed. | Authenticated multi-property PMS, onboarding, property/session/provider isolation remain **unimplemented or unaccepted** in this candidate. |
| PMS | Reservation preview/commit, availability and race-check source exist. HOLD branch adds 60-minute HOLD endpoints and migration zz114. | E2E booking, edit, HOLD expiry/race/confirm, cancellation, payment state, check-in/out and double-booking on unified candidate. |
| GREEN-API / WhatsApp | Owner-only QR/status adapter validates property binding, HTTPS provider URL and no-store response; explicitly returns `messaging_verified: false` and `ai_auto_send: false`. Polling pilot is marked SOURCE IMPLEMENTED, NOT ENABLED. | Live inbound → property-pinned CRM → outbound → provider message ID / delivery, deduplication and handoff; no production claim before provider evidence. |
| MARINA AI | Source documentation limits staff assistant to OWNER/MANAGER/RECEPTION and guest assistant to guest QR/PIN, read-only. | Test model/provider with role and hotel-specific knowledge, denial, no invented prices/availability. |
| Mobile | `apps/mobile/src/api/realApi.ts` uses the existing hotel-pinned API and HTTP cookie auth. `registry.ts` contains active workspaces for OWNER/MANAGER/MAID/TECHNICIAN; several other roles display profile only. Rooms derive from tasks, day summary raises unavailable. | Validate HTTPS reverse-proxy cookies, live backend, role claims, device QA and signed build; do not call it a finished all-role application. |
| OTA/payments | Current release manifest does not authorize payments, and official OTA provider E2E is not evidenced. | Only enable after official integrations and provider-level tests. |

## Release manifest consistency

In `release/marina-smart-current-candidate.json` on #272, `migration_count=38`, while one historical note says 37. On #276, the manifest is updated to 39 with a note specifying 39 migrations and 106 constraints. This is a **version-boundary/documentation mismatch**, not evidence that a running database has failed. Pin one candidate and validate actual migration names/constraints there.

## Next actions — strict order

1. **Do not touch MARINA_DEMO or Ubuntu.** Retain existing #244 / #272 / #276 / #273 branch boundaries.
2. Reconcile all intended P0 source changes into one **new, isolated candidate** using an explicit file/commit inventory. Do not auto-merge unrelated or cross-property changes.
3. Prove no regression in staff create and revocation with a disposable PostgreSQL + real HTTP test; isolate earlier root cause, don't infer it from UI behavior.
4. Run PMS, HOLD migration/rollback, cross-property denial, WhatsApp QR/AI permissions and mobile backend static checks on the **same SHA**. Record PASS/FAIL/SKIPPED by job URL and source SHA.
5. Fix only demonstrated MARINA defects with targeted tests. Do not claim the cross-product workflow failures are MARINA problems before reviewing failing job logs.
6. When the source gate passes, proceed to the separately agreed **Ubuntu read-only infrastructure inventory**, backup restore and then staging E2E. Production approval remains `false` until those steps pass.

**Audit boundary:** No server, Docker, database, external provider, DNS, payments, or demo configuration was changed or tested live during this source audit.
