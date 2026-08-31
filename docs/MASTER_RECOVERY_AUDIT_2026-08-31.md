# RESORT OS — MASTER RECOVERY AUDIT

Date: 2026-08-31
Repository: `stvelikiy-star/resort-os`
Audit base: `integration/site-pms-cms-20260827`
Audited integration head: `d157232b6c3069ddc14fa295bf0ef73d38d8b243`
Default `main` at audit time: `d19a235f8c471913561f1aae1c6d2860653c64d0`
Status: BASELINE RECOVERED / INTEGRATION RC CI-VERIFIED / EXTERNAL PRODUCTION NOT VERIFIED / NOT PRODUCTION READY

## CURRENT

The real current Resort OS release line is not the repository default `main`. The current integrated release candidate is PR #37 / branch `integration/site-pms-cms-20260827` at `d157232b6c3069ddc14fa295bf0ef73d38d8b243`.

The integrated release preserves the core authority chain:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

The exact integration head has the full set of PR-triggered workflow contours returned by GitHub as completed `success`, including Core, Full Staging, PMS mutations, payments, migration baseline, backup/restore, dependency security, AI, n8n and Beget production-hardening CI.

This proves repository/CI-local behavior. It does not prove external Beget runtime, public production, real provider/device behavior, rollback readiness or production room truth.

## EVIDENCE REVIEWED

Canonical knowledge:
- `knowledge/00_PRODUCT_BIBLE.md`
- `knowledge/01_DOMAIN_BUSINESS_RULES.md`
- `knowledge/02_SYSTEM_ARCHITECTURE.md`
- `knowledge/03_AI_ADMIN.md`
- `knowledge/04_CURRENT_STATE.md`
- `knowledge/05_DECISIONS_AND_BACKLOG.md`

Repository / history:
- default branch and branch protection state;
- branch inventory;
- commit history and PR history;
- PR #37 integration release line;
- compares `main -> integration`, `1be110c -> d157232`, and `d157232 -> 9ff651c`;
- open production/release issues #8, #28, #38, #39, #40;
- delivery handoff `docs/DELIVERY_HANDOFF_2026-08-30.md`.

Implementation:
- FastAPI Core booking/admin/auth/automation/AI/Telegram/Stay/PMS paths;
- Prisma schema and PostgreSQL constraints;
- migration chain;
- public/admin/staff Next.js packages;
- Caddy/Compose/Beget hardening material;
- CI security and regression workflows;
- Aug-31 My Stay branch implementation and migration.

External truth:
- currently reachable `www.3korony.com`;
- connected Google Sheet `НОМЕРНОЙ ФОНД — Три Короны — Production Import 84` and `OWNER_CHECKLIST`.

## WHAT WAS

The project evolved from a smaller Core/public/PMS baseline on `main` into multiple feature branches and then a unified integration release line. Important historical work includes:

1. Core CI and data-intake recovery.
2. Payment idempotency and transactional hardening.
3. Canonical knowledge recovery.
4. PostgreSQL migration baseline.
5. Public site truth/media work.
6. Control Center and CRM/inbox contours.
7. PMS iterations V3-V9, culminating in canonical V9.
8. DB-level active-task and inventory constraints.
9. Guest Services / Staff Operations.
10. Owner Intelligence, Owner Control V2, Growth Control and Executive Pack.
11. AI Administrator / AI Sales Draft / Telegram / n8n controlled adapters.
12. Single-server and later Beget-specific deployment hardening.
13. A separate Aug-31 My Stay / Dining / Smart Access extension, not yet admitted into the audited RC.

Several older open PRs represent staged or superseded development history. Their open state must not be interpreted as separate production-ready products.

## CHANGES

### Canonical release evolution

| Period / SHA | Area | Change | Current classification |
| --- | --- | --- | --- |
| 2026-08-26 `d19a235` | `main` | Canonical Current State v1.6 | HISTORICAL / STALE DEFAULT BRANCH |
| 2026-08-27..29 | Integration | Site + PMS V9 + Staff + CRM + owner/AI/automation contours unified | INTEGRATED |
| 2026-08-29 `1be110c` | Release evidence | 26/26 PR workflow contours green | VERIFIED HISTORICAL AUDIT BOUNDARY |
| 2026-08-29..30 | Deployment hardening | Beget compose/preflight/backup/release-contract changes | IMPLEMENTED + CI-VERIFIED ON LATER HEAD |
| 2026-08-30 `d157232` | Integration head | Full current integrated RC with later executable hardening | CURRENT AUDITED INTEGRATION HEAD |
| 2026-08-31 `9ff651c` | My Stay extension | Guest session, dining, charges, smart access, admin/staff UI | IMPLEMENTED / NOT VERIFIED / NOT RC |

## WHAT IS NOW

### Architecture

Repository type: monorepo / modular monolith.

Applications and runtime:
- Public Web: Next.js 15.5.24 / React 19.2.8.
- Admin/PMS: Next.js 15.5.24 / React 19.2.8.
- Staff PWA: Next.js 15.5.24 / React 19.2.8.
- Core API: FastAPI 0.116.1 / Python.
- Database: PostgreSQL + Prisma schema/migrations + explicit SQL constraints.
- Automation: n8n adapters/contracts; no direct automation DB authority.
- AI: controlled Core-backed public AI + manager-review AI Sales Draft.
- Deployment: Caddy + container topology; Beget-specific package exists in source/CI, external host not verified.

No evidence requires microservices/Kafka/Kubernetes. `EXTEND > REWRITE` remains correct.

### Domain state

- Property: IMPLEMENTED for current property-scoped V1.
- Generic Tenant / multi-property tenancy: PARTIAL / TARGET NOT IMPLEMENTED.
- ReservationRequest: VERIFIED.
- Confirmed Reservation: VERIFIED through controlled human/payment flow.
- Guest: VERIFIED.
- Persisted canonical Stay entity: NOT IMPLEMENTED; lifecycle behavior currently rides Reservation + InventoryBlocks.
- Rooms/Room Types: VERIFIED in development baseline; production physical mapping BLOCKED by owner truth.
- Room assignment / Split Stay: VERIFIED on PMS V9.
- Availability: VERIFIED with DB overlap constraint + transactional mutation path.
- Pricing: VERIFIED for current deterministic approved rate-plan contours; generic business-rule matrix remains incomplete/decision-bound.
- Folio: PARTIAL. Reservation totals + Payments exist; complete canonical Folio/Charge model is not present in audited RC.
- Payments: VERIFIED current controlled/idempotent path.
- Guest Services / Tasks: VERIFIED current V1 operational contour.
- Housekeeping / Maintenance: VERIFIED current V1 operational contour.
- Guest Portal / My Stay: IMPLEMENTED ON SEPARATE BRANCH, NOT VERIFIED, NOT RC.
- AI Administrator: IMPLEMENTED + CI-VERIFIED current bounded contours; target generic tool ecosystem remains partial.
- Omnichannel: PARTIAL; contracts exist, live providers not externally verified.

## VERIFIED

The following are supported by current integration source plus exact-head CI evidence:

- Reservation Request and human confirmation boundary.
- Automation/n8n cannot directly confirm payment or create a guaranteed Reservation.
- AI Sales is manager-review draft only and does not auto-send.
- Public AI uses Core-backed facts and has no reservation/payment authority.
- PMS V9 preview -> explicit commit mutation model.
- Split Stay via contiguous InventoryBlock schedule segments.
- Reservation/version locking and deterministic room locking during PMS mutation.
- DB exclusion protection against overlapping active room blocks.
- conflict recheck before PMS commit and race -> HTTP 409 fail-closed behavior.
- TECH_BLOCK target protection and CLEAN check-in gate.
- checked-in historical room nights cannot be rewritten.
- checkout -> room DIRTY -> housekeeping task deterministic flow.
- payment idempotency and migration/backup-restore CI contours.
- public/admin/staff application builds in the release workflow contours.
- Beget deployment package syntax/build/preflight contract in CI.

## IMPLEMENTED NOT VERIFIED

### My Stay / Dining / Smart Access — branch `feat/my-stay-integration-v1-20260831`

The branch is 15 commits ahead of current integrated RC and adds:
- secure guest activation/session logic;
- `/my-stay` UI;
- guest service request flow;
- dining orders/menu/charges;
- dining staff surface;
- smart access points/grants/controller integration;
- migration `5_my_stay`.

The exact branch head had no GitHub Actions runs at audit time. It must not be called VERIFIED or included in the current release candidate.

Positive security design already present:
- QR/room URL is not treated as identity;
- one-time high-entropy activation token + 6-digit PIN;
- HttpOnly guest session;
- expiry/revocation;
- reservation binding and `CHECKED_IN` requirement;
- room smart-access point bound to current room context;
- smart-access controller HMAC and fail-closed inactive points.

## PARTIAL

1. Persisted `Stay` domain entity: target approved, current behavior represented through Reservation state + room schedule.
2. Generic tenancy: property-scoped V1 exists, generic Tenant model does not.
3. Folio: accommodation total/payment exists; full generic Folio/Charge/Adjustment/Void model is incomplete.
4. Omnichannel: Telegram/n8n contracts implemented; real launch providers remain external-unverified.
5. AI Administrator: bounded real contours implemented; general user-context controlled tool ecosystem remains target work.
6. Monitoring/observability: deployment contracts exist; actual external alerts/restart/restore monitoring not verified.

## BROKEN

No evidence was found that the audited integration RC violates the core Reservation/payment authority boundary.

The following defects/gaps were found outside the accepted RC or in release governance:

- canonical `main` is stale and unprotected;
- `04_CURRENT_STATE.md` on integration was stale relative to its own later executable head;
- My Stay migration changes database shape without a matching Prisma schema update in that branch;
- My Stay guest dining POST has no explicit idempotency key contract;
- My Stay guest activation has no demonstrated application-level brute-force rate limit/lockout;
- staff login on current RC has no demonstrated application-level brute-force rate limit/lockout;
- dependency security workflow gates Node HIGH/CRITICAL but no backend Python vulnerability scanner was found in the audited security contour.

## UNKNOWN

- externally measured production performance/capacity;
- actual Beget VPS/DBaaS/S3 runtime state;
- real external WSS behavior;
- real WhatsApp/other provider behavior not separately accepted;
- real device behavior until device acceptance;
- unresolved physical room location facts in owner checklist;
- business rules explicitly marked UNKNOWN / DECISION REQUIRED in canonical Business Rules.

## BLOCKED

Production claims remain blocked by external/owner evidence:

1. Beget account/VPS access and non-destructive host preflight.
2. Verified complete rollback backup of the legacy live site.
3. External HTTPS/WSS staging.
4. Owner-confirmed 84-room physical production register.
5. Real browser/mobile/provider/device acceptance.
6. Backup/restore rehearsal and monitoring on the real external topology.
7. Explicit owner production cutover approval.

## CRITICAL ERRORS

### P0 release blockers

P0-R1 — External Beget staging is not verified.
Impact: cannot claim production ready/live/autonomous.

P0-R2 — Legacy live rollback backup is not verified.
Impact: unsafe to overwrite/switch the current site.

P0-R3 — Physical 84-room production register is not owner-confirmed.
Impact: production inventory import could encode incorrect physical truth.

P0-R4 — Live public site remains legacy/stale and is not the audited Resort OS release.
Impact: public product truth differs from canonical owner-approved Resort OS truth.

These are release blockers, not proof that the CI-verified application core is broken.

## BUSINESS RULE VIOLATIONS

Audited RC:
- no confirmed violation found for `ReservationRequest != Confirmed Reservation` in inspected active paths;
- no confirmed AI/n8n bypass of human reservation/payment authority found;
- no frontend-only availability/pricing authority found in PMS mutation path.

Live legacy public site:
- displays stale claims that conflict with the accepted Resort OS public-truth boundary and therefore must not be used as evidence for current product capability.

## SECURITY FINDINGS

| ID | Severity | Finding | Status / action |
| --- | --- | --- | --- |
| SEC-01 | P1 | Staff login has no demonstrated app-level brute-force throttling/lockout | Add bounded rate limit/lockout + tests before production exposure |
| SEC-02 | P1 | My Stay guest activation has no demonstrated brute-force throttling/lockout | Block My Stay enable until fixed/tested |
| SEC-03 | P1 | My Stay schema migration not reflected in Prisma schema | Repair schema/migration contract before merge |
| SEC-04 | P2 | Python dependency CVE gate not found; current dependency-security workflow is Node-focused | Add backend dependency audit |
| SEC-05 | VALIDATE | Physical smart-access controller E2E not verified | Keep access points inactive until external acceptance |

No production secret was exposed in the inspected source. This is not a substitute for repository secret scanning and external secret-management verification.

## DATA INTEGRITY / CONCURRENCY

Verified current RC protections:
- PostgreSQL active room overlap exclusion constraint;
- transaction + row locks on booking/payment/PMS critical mutations;
- payment idempotency;
- PMS stale-version protection;
- conflict recheck before mutation;
- room lock ordering to reduce deadlocks;
- Split Stay contiguity checks.

My Stay pre-merge gaps:
- dining order creation lacks explicit idempotency key, so retry/double-click behavior must be made deterministic;
- guest service duplicate prevention requires adversarial first-insert concurrency proof / DB invariant review.

## ARCHITECTURE FINDINGS

1. Current modular monolith is compatible with target principles and should be extended, not rewritten.
2. Resort Core + PostgreSQL remain operational authority.
3. Next.js interfaces and n8n are adapters/surfaces, not sources of truth.
4. Separate persisted Stay and generic tenancy remain legitimate future domain evolution, not prerequisites for preserving current V1 correctness.
5. My Stay is an extension and should remain isolated until schema/security/idempotency/CI gates pass.

## DOCUMENTATION DRIFT

DRIFT-01:
`knowledge/04_CURRENT_STATE.md` states post-`1be110c` changes are documentation-only. Git history shows later executable Beget deployment/hardening and release-contract changes. Current State must move its audited boundary to a later exact verified head or explicitly classify those changes.

DRIFT-02:
Default `main` still contains an older Current State and is not the current release line. Issue #40 correctly requires promotion only after external staging acceptance.

DRIFT-03:
Aug-31 My Stay code exists on a separate branch but is not part of canonical Current State and has no exact-head CI evidence.

## PREVIOUS PLAN

Recovered release plan from Current State, delivery handoff and open release issues:

1. Build integrated release candidate and prove it in CI-local staging.
2. Harden production package/migrations/backup contracts.
3. Obtain Beget access and run host preflight.
4. Capture verified full rollback of current legacy `3korony.com`.
5. Deploy isolated external staging without changing live DNS.
6. Import only owner-confirmed physical room truth.
7. Run external public truth, PMS, staff, browser/mobile/WSS/provider acceptance.
8. Verify backup/restore, restart and monitoring.
9. Capture fresh cutover evidence.
10. Get explicit owner production switch approval.
11. Cut over and run post-cutover smoke/monitoring.
12. Only after external acceptance, promote the accepted exact release to protected `main` + immutable tag.

## PREVIOUS PLAN STATUS

| Plan item | Status |
| --- | --- |
| Integrated RC | VERIFIED IN CI |
| CI-local staging | VERIFIED |
| Production package | VERIFIED IN CI |
| Migration baseline | VERIFIED IN CI |
| Backup/restore mechanics | VERIFIED IN CI |
| Beget hardening contract | VERIFIED IN CI |
| Actual Beget host preflight | BLOCKED / NOT VERIFIED |
| Legacy full rollback capture | BLOCKED / NOT VERIFIED |
| External staging | BLOCKED / NOT VERIFIED |
| Owner-confirm 84 physical rooms | BLOCKED / OPEN |
| Real device/provider acceptance | BLOCKED / NOT VERIFIED |
| Production cutover | NOT AUTHORIZED |
| Protected canonical `main` + release tag | PLANNED AFTER EXTERNAL ACCEPTANCE |
| My Stay extension | IMPLEMENTED NOT VERIFIED / OUTSIDE CURRENT RC |

## TARGET VS CURRENT — EXECUTIVE TABLE

| Domain | Target | Current | Evidence status | Gap | Priority | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| Platform | One Core modular platform | Modular monolith | VERIFIED | External production | P0 | External staging |
| Property/Tenant | Property -> multi-property | Property-scoped V1 | PARTIAL | Generic tenancy | P2/DEFER | Design only when scope requires |
| Auth/RBAC | Server enforced | Argon2/session/RBAC | VERIFIED core | Login throttling | P1 | Add rate-limit before prod |
| Reservation Request | Separate from Reservation | Separate | VERIFIED | none critical | — | preserve |
| Confirmed Reservation | Human confirmation | Manager/payment controlled | VERIFIED | none critical | — | preserve |
| Guest | Canonical guest | Implemented | VERIFIED | privacy regression tests continue | P1 | external acceptance |
| Stay | Persisted Stay + room segments | Reservation lifecycle + segments | PARTIAL | No persisted Stay entity | P2 | evolve later |
| Rooms | Physical truth | 84/12 dev baseline | PARTIAL | Owner mapping | P0 | close #38 |
| Room Assignment | Multiple segments | InventoryBlocks | VERIFIED | persisted Stay relation later | P2 | preserve |
| Split Stay | Required | PMS V9 | VERIFIED | none critical | — | preserve |
| Availability | Backend authoritative | DB exclusion + Core | VERIFIED | external runtime | P0 | staging acceptance |
| Pricing | Backend deterministic | Rate plan/Core | VERIFIED current contour | incomplete generic rules | DECISION | do not invent |
| Folio | Canonical accounting model | partial total/payment | PARTIAL | Full Folio/Charge | P2 | separate domain phase |
| Payments | Controlled/auditable/idempotent | implemented | VERIFIED | real provider acceptance if launch | P0 external | staging/provider E2E |
| Tasks | reusable operations | OperationalTask | VERIFIED V1 | broader generic task domain later | P2 | preserve |
| Housekeeping | deterministic lifecycle | implemented | VERIFIED | external device | P0 external | staging/device E2E |
| Maintenance | deterministic lifecycle | implemented | VERIFIED | external device | P0 external | staging/device E2E |
| Guest Portal | Stay-bound secure guest context | separate My Stay branch | IMPLEMENTED NOT VERIFIED | security/schema/idempotency/CI | P1 | harden before merge |
| AI Administrator | controlled tools, no extra authority | bounded real contours | VERIFIED current contour | generic tool/context expansion | P2 | extend later |
| Omnichannel | adapters, Core authority | Telegram/n8n contracts | PARTIAL | live provider evidence | P0 if launch | external E2E |
| Security | least authority + isolation | strong core, gaps listed | PARTIAL | throttling/Python audit/external | P1 | harden |
| Testing | regression evidence | broad GitHub Actions suite | VERIFIED RC | My Stay no runs | P1 | exact-head CI before merge |
| Deployment | recoverable external runtime | package CI only | BLOCKED external | Beget/rollback/monitoring | P0 | #28 + #8 |

## GAP REGISTER

| ID | Domain | Gap | Severity | Dependency | Action |
| --- | --- | --- | --- | --- | --- |
| GAP-001 | Deployment | No external Beget staging evidence | P0 | Beget access | Run host preflight + isolated staging |
| GAP-002 | Recovery | No verified legacy rollback archive | P0 | Hosting access | Capture/checksum/restore evidence |
| GAP-003 | Rooms | 11 P0 owner-check groups unresolved | P0 | Owner facts | Complete owner checklist; dry-run import |
| GAP-004 | Repository | `main` stale/unprotected | P1 | External staging acceptance | Promote accepted SHA then protect/tag |
| GAP-005 | Documentation | Current State lagged executable head | P1 | none | Update canonical knowledge in this recovery PR |
| GAP-006 | Auth | Login brute-force protection not demonstrated | P1 | none | Add rate-limit/lockout + regression |
| GAP-007 | My Stay | No exact-head CI | P1 | isolated branch | Add/execute CI before integration |
| GAP-008 | My Stay DB | Migration/Prisma drift | P1 | GAP-007 | Update schema + migration validation |
| GAP-009 | My Stay | Dining order idempotency absent | P1 | GAP-007 | Add idempotency + retry/concurrency tests |
| GAP-010 | My Stay | Guest activation brute-force control absent | P1 | GAP-007 | Add rate limit/lockout tests |
| GAP-011 | Security | Python dependency vulnerability scan absent | P2 | none | Add pip dependency audit |
| GAP-012 | Domain | Persisted Stay absent | P2 | product sequencing | Minimal later evolution |
| GAP-013 | Domain | Generic tenancy absent | P2/DEFER | multi-property scope | Do not pre-emptively redesign |
| GAP-014 | Finance | Full Folio model absent | P2 | approved finance rules | Separate finance domain phase |

## ERROR REGISTER

| ID | Severity | Domain | Problem | Impact | Root cause | Fix | Dependency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ERR-001 | P0 | Release | External staging missing | No production evidence | Access/acceptance not performed | #28 sequence | Beget access |
| ERR-002 | P0 | Recovery | Legacy rollback unverified | Unsafe cutover | Hosting backup not captured | #8 sequence | Hosting access |
| ERR-003 | P0 | Data truth | Physical room mapping unresolved | Incorrect prod inventory risk | Missing owner facts | #38 checklist | Owner |
| ERR-004 | P1 | Governance | Default main stale/unprotected | Wrong branch may be deployed | Release line evolved outside main | #40 after staging | External acceptance |
| ERR-005 | P1 | Docs | Current State old executable boundary | False baseline | Later executable commits not reflected | docs recovery | none |
| ERR-006 | P1 | My Stay | DB migration / Prisma mismatch | schema drift | extension changed SQL only | align schema + validation | My Stay branch |
| ERR-007 | P1 | My Stay | dining POST lacks idempotency | duplicate order/charge on retry | no request idempotency contract | add key + DB uniqueness/test | My Stay branch |
| ERR-008 | P1 | Security | guest/staff brute-force controls not demonstrated | credential attack surface | no rate-limiter found | bounded throttling/lockout | pre-prod |
| ERR-009 | P2 | Security | Python dependency CVE gate missing | coverage gap | Node-focused security workflow | add backend audit | none |

## DECISION REQUIRED REGISTER

Only genuine owner decisions remain here:

1. **Physical room truth (#38).**
Why: repository/Drive evidence cannot authoritatively infer building/floor/sellability for the 11 P0 groups.
Recommended: answer group rules once, not room-by-room where a common rule is valid.
Consequence: production room import remains blocked until complete.

2. **Production cutover approval.**
Why: DNS/public switch is production/irreversible-risk work.
Recommended: only after external staging + rollback + room truth + backup/monitoring evidence.
Consequence: no production switch without explicit approval.

3. **Business rules still marked DECISION REQUIRED in `01_DOMAIN_BUSINESS_RULES.md`.**
Why: technical implementation must not invent pricing/refund/financial rules.
Recommended: resolve only when the corresponding V1 domain is scheduled.

No owner decision is required for ordinary technical repairs such as documentation drift, CI, rate limiting, dependency audit or My Stay schema/idempotency fixes.

## PLAN FROM CURRENT TO TARGET

### PHASE 0 — BASELINE RECOVERY
Status: COMPLETED BY THIS AUDIT, pending review/merge of docs recovery.
- recover canonical target/rules/architecture;
- reconstruct history/branches/PRs;
- establish integrated RC vs stale main;
- classify current/My Stay/external production separately;
- repair canonical Current State drift.

### PHASE 1 — P0 RELEASE CORRECTNESS
1. Obtain Beget access and run non-destructive host preflight.
2. Capture verified legacy rollback archive and DNS/runtime facts.
3. Complete owner-confirmed 84-room physical map.
4. Deploy isolated external staging from explicitly accepted/re-verified SHA.
5. Apply reviewed migration chain.
6. Execute public truth/PMS/staff/browser/mobile/WSS/provider acceptance.
7. Verify backups, restart behavior, monitoring and restore rehearsal.

### PHASE 2 — RELEASE GOVERNANCE
1. Reconcile any staging defects by minimal fixes only.
2. Re-run exact-head release suite.
3. After acceptance, promote exact accepted release to `main`.
4. Protect `main` and tag immutable release.
5. Record tag -> SHA -> image -> deployment linkage.

### PHASE 3 — MY STAY HARDENING
Do not merge/enable before its independent gates:
1. align Prisma schema with migration;
2. add guest activation brute-force control;
3. add dining idempotency;
4. prove guest-request concurrency behavior;
5. add exact-head migration/security/API/browser tests;
6. keep smart access inactive until controller E2E;
7. integrate only after green review.

### PHASE 4 — CORE DOMAIN EVOLUTION
Dependency/business-value ordered, not rewrite-driven:
- persisted Stay when required;
- full Folio/Charge accounting after rules approval;
- generic tenancy when multi-property becomes actual scope;
- broader Service/Resource engine where operational need is proven.

### PHASE 5 — AI / OMNICHANNEL EXPANSION
Only after corresponding deterministic Core capabilities and permission policies exist.

## NEXT TASK

TASK ID: RELEASE-P0-EXT-STAGING
Title: Establish real Beget external staging baseline
Priority: P0

Why this task:
- application-level integration is already broadly CI-verified;
- the critical path is no longer another UI/module;
- production truth cannot advance without external host/rollback/runtime evidence;
- issue #40 explicitly defers main cleanup until external staging acceptance.

Target result:
- recorded non-destructive host preflight;
- verified rollback capture path;
- isolated staging hostname/runtime;
- exact deployed SHA;
- HTTPS/WSS/secure-cookie/CORS acceptance;
- staging DB migration ledger;
- external acceptance evidence without touching live DNS.

Dependencies:
- actual Beget access/credentials;
- no production DNS change authorization is implied;
- room import waits for #38 owner truth.

Implementation plan:
1. run `scripts/host_preflight.sh` read-only;
2. record OS/Docker/DNS/network/storage/runtime facts;
3. identify current legacy web root/DB/uploads/config for rollback capture;
4. provision isolated staging topology;
5. deploy exact accepted/re-verified release;
6. apply migrations through `prisma migrate deploy` only;
7. run external probes and acceptance suite;
8. record evidence and defects;
9. stop before live cutover until explicit owner approval.

Test plan:
- health/readiness;
- HTTPS and secure cookies;
- WSS upgrade/reconnect;
- public truth probe;
- booking Request boundary;
- manager confirmation/payment authority;
- PMS Split Stay/conflict/stale tests;
- staff housekeeping/maintenance;
- backup + restore rehearsal;
- reboot/restart behavior;
- provider/device tests only for launch scope.

Acceptance criteria:
- external staging evidence is reproducible;
- no live DNS/public cutover occurred;
- exact deployed SHA recorded;
- rollback evidence exists before any future cutover;
- all blocking failures are registered, not hidden.

Current blocker:
- no connected Beget/SSH capability is available in the current tool environment and no Beget plugin is installed.

Owner action required only to execute this P0 external task:
- provide/authorize actual Beget VPS/account access through an available secure connection method;
- separately provide the missing authoritative physical-room answers for issue #38 before production room import.

## OWNER-FACING SUMMARY

CURRENT: integrated Resort OS RC is CI-verified and substantially functional; production is not externally verified and current live site is still legacy.

ACTION: recovered target, rules, architecture, git/PR history, current code/DB/test evidence, release gates, Drive room truth and fresh My Stay branch.

RESULT: no core Reservation/payment authority bypass was found in audited active contours; PMS/inventory/payment safety is materially implemented and tested; the main risks are external production gates, stale repository governance, and unverified My Stay extension gaps.

NEXT: external Beget staging baseline is the critical-path task.

BLOCKER: Beget access plus owner physical-room truth are external evidence gates.

OWNER ACTION: grant secure Beget access for non-destructive staging work and complete the 11 P0 room-truth groups; no DNS cutover approval is requested at this stage.
