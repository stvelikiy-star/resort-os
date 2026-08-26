# THREE CROWNS — ACTIVE EXECUTION PLAN

Version: 1.4
Date: 2026-08-26
Status: SUPPORTING ACTIVE EXECUTION PLAN
Canonical: NO
Scope: Current delivery order for «Три Короны»
Authority:
- canonical Product/Domain/Architecture/AI truth: `00`–`03`;
- factual implementation reality: `04_CURRENT_STATE.md` only;
- approved decisions / validation / backlog: `05_DECISIONS_AND_BACKLOG.md` only;
- this file only sequences already approved/evidence-backed Three Crowns work.

Critical rule: **PLAN != CURRENT STATE. PLAN != CANONICAL DECISION.**

If this plan conflicts with `04` about what exists, `04` controls. If it conflicts with `05` about what is approved/open/deferred, `05` controls.

---

## 1. Frozen / deferred scope

NFC / wristband / internal-wallet work is DEFERRED under D-021 and excluded from the active Three Crowns V1 engineering queue.

Dormant NFC source/schema evidence may remain. No NFC feature development, provider integration, UX expansion or production activation may resume without a new explicit canonical decision in `05`.

Also do not activate unspecified dining/store/access/QR/billiards/LED business rules without evidence and required decisions.

---

## 2. Approved Three Crowns operating priorities

Canonical decision owner: `05_DECISIONS_AND_BACKLOG.md`.

Active approved boundaries:
1. PMS chessboard is the primary daily operating surface (D-022).
2. PMS/reception/operations/finance/public availability use the same Resort Core truth.
3. Client-channel orchestration is through n8n over controlled Core APIs (D-019).
4. Three Crowns V1 prepayment is manager-decided, manager-collected and manager-recorded; automated acquiring is not a V1 gate (D-020).
5. NFC remains deferred (D-021).

Factual implementation/verification of these boundaries is recorded only in `04_CURRENT_STATE.md`.

---

## 3. Client automation delivery boundary

Approved path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- other client channels may use n8n where appropriate;
- public booking website -> Resort Core directly.

n8n / AI may:
- collect dates, guest count and contact data;
- call Core for deterministic availability/current price facts;
- answer approved hotel questions from authoritative facts;
- create/read ReservationRequest;
- hand a qualified request to management.

n8n / AI must not:
- write PostgreSQL directly;
- invent availability/price/policy;
- choose prepayment amount/method;
- collect/approve money;
- bypass manager-controlled conversion to guaranteed Reservation;
- check-in/out/refund or mutate hotel money.

Direct provider adapters retained in the repository are optional/reference code, not an active V1 dependency.

---

## 4. Finance delivery boundary

Three Crowns active V1 finance is internal hotel operational control only.

Allowed current product direction:
- reservation value;
- manager-confirmed received payment/prepayment facts;
- outstanding balance derived from stored facts;
- recorded method/reference/note where management enters them;
- internal summaries/audit.

Not an active V1 requirement:
- automatic acquiring;
- generated payment links/QR;
- automatic prepayment percentage;
- generic accounting profit/tax/revenue recognition;
- provider selection merely because generic Resort OS payment scenarios remain under validation.

Generic product payment-provider questions remain in `05` VALIDATE queue.

---

## 5. Verified implementation is not work-to-do

The following areas are already represented in `04_CURRENT_STATE.md` as current CI-covered development baseline and must not be repeatedly re-created as new backlog merely because older versions of this execution plan listed them:
- transactional PMS chessboard mutation contracts;
- reception/reservation workspace baseline;
- check-in/check-out safety;
- housekeeping/maintenance transition safety;
- internal manager-recorded finance baseline;
- n8n/Core contract baseline;
- public site build baseline;
- restored CI/Data Intake/NFC-scope verification;
- payload-bound/concurrency-safe payment idempotency.

Further changes to these areas require a new evidenced GAP or decision, not automatic continuation from stale checklist items.

---

## 6. Current delivery order

Based on the verified Current State in `04`, the active remaining delivery order is:

1. **Production migration baseline**
   - inspect current Prisma schema + active PostgreSQL constraints;
   - generate baseline using the reviewed helper;
   - review generated SQL;
   - prove it against a clean staging-equivalent database before any production claim.

2. **Production-like backup / restore rehearsal**
   - use the intended migration/deploy procedure;
   - verify restored schema/data/critical constraints;
   - retain evidence.

3. **Staging acceptance**
   - Core health/readiness;
   - PMS / reception / operations / finance;
   - Staff PWA;
   - public booking flow;
   - n8n/Core handoff contract;
   - negative/security boundaries where applicable.

4. **Owned public-site media and visual acceptance**
   - replace temporary/hotlinked imagery with owned Three Crowns photography;
   - verify responsive presentation after replacement.

5. **Production environment hardening**
   - production secrets;
   - HTTPS/hostnames;
   - monitoring/alerts/logging checks.

6. **Rollback rehearsal**
   - verify rollback procedure against intended deployment path.

7. **Explicit owner cutover gate**
   - DNS/traffic switch only after prior production gates have evidence.

If staging/production credentials or infrastructure are unavailable, mark the relevant step BLOCKED and complete only repo-local preparation/evidence. Do not fabricate staging/production verification.

---

## 7. Work that may proceed without new product decisions

Only when it stays inside existing canonical boundaries:
- migration SQL generation/review tooling;
- clean disposable-database verification;
- backup/restore tooling and reproducible tests;
- deployment/preflight/health/readiness/logging/monitoring scaffolding;
- evidence-backed fixes to failures reproduced by those gates;
- owned-media integration after media is actually supplied/available;
- staging verification when authorized environment access exists.

Do not introduce new commercial/domain rules while doing infrastructure work.

---

## 8. Work that must not be invented

Do not invent:
- automatic repricing/compensation policy for changed dates/category/room;
- automated prepayment amount/terms/payment collection;
- cancellation/refund/no-show penalties;
- walk-in/group/waitlist rules;
- early-arrival/late-departure charges;
- exact dining/store/service/access/QR/billiards/LED rules;
- acquiring/provider behavior without a canonical decision and verified integration requirements;
- production ManyChat/API Green credentials;
- production financial values or hotel facts not read from authoritative sources.

---

## 9. Verification rule

Every change starts as IMPLEMENTED, not VERIFIED.

Required progression:

`CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> UPDATE 04_CURRENT_STATE.md`

GitHub Actions/infrastructure failures that occur before workflow steps execute must be classified as infrastructure evidence, not automatically as application-test failures.

This supporting plan should be updated when the active order materially changes, but it must never become a second Current State or second decision registry.
