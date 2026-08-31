# RESORT OS — CURRENT STATE

Version: 2.7
Date: 2026-08-31
Status: INTEGRATION RELEASE CANDIDATE / EXACT-HEAD CI VERIFIED / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository: `stvelikiy-star/resort-os`
Current integration branch: `integration/site-pms-cms-20260827`
PR: `#37`

CURRENT AUDITED INTEGRATION HEAD: `d157232b6c3069ddc14fa295bf0ef73d38d8b243`
AUDIT DATE: 2026-08-31

GitHub returned **27 PR-triggered workflow contours associated with this exact head; all 27 completed `success`**.

The successful contours include:
- Resort Core CI;
- Three Crowns Full Staging Gate;
- PMS Chessboard Mutation CI;
- Realtime PMS CI;
- Payment Idempotency CI;
- Production Migration Baseline CI;
- PostgreSQL Backup Restore CI;
- Single Server Production Package CI;
- Beget Production Hardening CI;
- Dependency Security Inspection;
- Public Site Truth CI;
- Guest Services PMS CI;
- Hotel Operations CI;
- Owner Intelligence CI;
- Owner Control V2 CI;
- Owner Growth Control CI;
- Unified Inbox CI;
- Control Center Contract CI;
- AI Administrator CI;
- AI Sales Draft CI;
- Telegram Sales CI;
- Automation Contract CI;
- n8n Resort Core Contract CI;
- n8n Workflow JSON CI;
- Data Intake Integrity CI;
- Staff Voice CI;
- NFC Deferred Scope CI.

Previous canonical text treated `1be110c35e1e7d5876cae40a1b58cef42bd10a22` as the last audited executable boundary and described later commits as documentation-only. Recovery audit proved that the branch contains later executable Beget/release-hardening changes. The canonical evidence boundary is therefore advanced to exact head `d157232...`, which has its own exact-head workflow evidence.

Detailed recovery evidence: `docs/MASTER_RECOVERY_AUDIT_2026-08-31.md`.

## Repository governance

Default branch `main` is still at historical SHA `d19a235f8c471913561f1aae1c6d2860653c64d0` and is not the current integrated RC. It is also unprotected at this audit point.

This is a **P1 release-governance gap**, not permission to merge the RC immediately. Issue #40 correctly requires promotion of the externally accepted exact release to protected `main` only **after external Beget staging acceptance**.

Do not deploy old `main` as if it were current product truth.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Critical invariants remain intact in the audited RC:
- `ReservationRequest != Confirmed Reservation`;
- human manager confirmation/payment authority is mandatory;
- AI/n8n cannot confirm payment or guarantee Reservation;
- n8n does not receive direct Resort OS database authority;
- Sheets/reports/snapshots are read/control surfaces, not booking/payment truth;
- frontend is not the authority for PMS conflict/availability;
- NFC remains deferred.

## Database

Verified audited-RC migration chain:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements`

Verified by repository CI contours:
- clean migration deployment;
- exact migration ledger;
- 84-room / 12-category development seed;
- PostgreSQL inventory overlap protection;
- payment/idempotency constraints;
- Guest Services constraints;
- Growth/snapshot constraints;
- migration-aware backup -> clean restore.

The **production physical room register is not owner-confirmed**. Connected Sheet `НОМЕРНОЙ ФОНД — Три Короны — Production Import 84` still has 11 P0 owner-check groups open. Production room reconciliation/import remains fail-closed.

## PMS / Reservation / Stay

PMS V9 remains canonical and CI-verified for current RC.

Verified current mutation model:
- server preview -> explicit commit;
- contiguous one-or-many room schedule segments;
- move / resize / Split Stay;
- transaction-bound mutation;
- reservation version stale protection;
- deterministic room locking;
- conflict recheck;
- PostgreSQL exclusion race protection;
- TECH_BLOCK target protection;
- CLEAN check-in gate;
- CHECKED_IN historical room nights immutable;
- audit history;
- immediate room move marks vacated room DIRTY and creates/reuses housekeeping work.

A separate persisted canonical `Stay` entity is **not implemented** in audited RC. Current stay lifecycle is represented through Reservation state plus InventoryBlocks/room schedule. Classification: **PARTIAL relative to target**, not broken V1.

## Availability / Pricing

Current PMS availability/conflict authority is backend/database-owned.

Pricing preview is deterministic through Resort Core/rate-plan data. PMS schedule movement may produce a suggested recalculated total/delta but deliberately does **not** silently mutate the stored Reservation commercial total.

Generic pricing/business-rule cases explicitly left UNKNOWN/DECISION REQUIRED in `01_DOMAIN_BUSINESS_RULES.md` remain unresolved and must not be invented.

## Payments / Finance

Current controlled payment path and payload-bound idempotency are CI-verified.

Complete canonical Folio/Charge/Adjustment/Void accounting remains **PARTIAL / NOT IMPLEMENTED** in the audited RC. Management metrics are not statutory accounting.

## Guest Services / Staff Operations

Current V1 contours are CI-verified:
- Reservation-linked Guest Services through OperationalTask;
- housekeeping lifecycle;
- maintenance/TECH_BLOCK behavior;
- inspection/rework/acceptance contours;
- staff role boundaries;
- checkout -> DIRTY -> housekeeping task deterministic transition.

Guest Services do not automatically alter accommodation total or create Payment.

## Owner Intelligence / Control / Growth / Executive

The integrated RC retains the CI-verified owner surfaces described in delivery handoff:
- repeat-Guest fail-closed identity and Guest history;
- room/payment/service/conversation drill-down;
- 84-room management heatmap;
- factual period comparison;
- 7/30-day on-books control;
- Action Center;
- analytics snapshots;
- snapshot-based booking pickup with fail-closed insufficient history;
- Growth queues and factual NPS/sample size;
- Executive Pack management summary.

Governance boundary remains:

`outbound_authority = NONE_AUTOMATIC`

Growth candidate != marketing consent.

## AI Administrator / AI Sales

Canonical AI rules remain:

`AI_PERMISSION <= CURRENT_USER_PERMISSION`

`SOURCE OF TRUTH = RESORT OS`

Audited implementation evidence:
- public AI uses Core-backed property/availability facts;
- public AI does not create confirmed Reservation or collect payment;
- AI Sales creates INTERNAL manager-review drafts only;
- `auto_send_enabled = false`;
- automation endpoint creates ReservationRequest only and explicitly forbids payment/guaranteed-reservation/refund authority.

Live external provider/device behavior remains NOT VERIFIED.

## Security

Verified current RC protections include:
- Argon2 password hashing;
- server-side session lookup/revocation/expiry;
- server-side RBAC/property checks;
- HttpOnly staff session cookie;
- Node dependency security workflow gates HIGH/CRITICAL npm findings;
- webhook/service-auth boundaries in their tested contours;
- database transaction/constraint protections for critical booking/payment/PMS paths.

Open security gaps:
- staff login application-level brute-force throttling/lockout is not demonstrated;
- backend Python dependency vulnerability scanning is not demonstrated by the current Node-focused dependency-security workflow;
- external HTTPS/secure-cookie/CORS/WSS behavior is not verified until real staging.

No production secret was exposed in the inspected audit paths. This does not replace repository secret scanning or external secret-management verification.

## My Stay / Guest Portal extension — separate branch

Branch: `feat/my-stay-integration-v1-20260831`
Head audited: `9ff651c17f1fa0f38711cc900317c3a2f3f90fd4`
Relationship: 15 commits ahead of `d157232...`, 0 behind at audit time.

Status: **IMPLEMENTED / NOT VERIFIED / NOT PART OF CURRENT RC / DO NOT ENABLE**.

The branch adds:
- guest activation/session context;
- `/my-stay` UI;
- dining/menu/orders/ancillary charges;
- guest operational requests;
- dining staff UI;
- smart access points/grants/controller adapter;
- migration `5_my_stay`.

Positive design:
- QR/room URL is not identity;
- one-time high-entropy activation token + 6-digit PIN;
- HttpOnly guest session;
- expiry/revocation;
- Reservation binding and CHECKED_IN gate;
- current-room binding for ROOM access;
- smart-access controller HMAC;
- physical access points default inactive/fail-closed.

Blocking findings before integration:
1. exact branch head had no GitHub Actions runs at audit time;
2. migration `5_my_stay` changes DB schema without a matching `schema.prisma` change in branch diff;
3. guest activation has no demonstrated application-level brute-force rate limit/lockout;
4. dining order creation has no explicit idempotency key contract, so retry/double-click duplicate behavior is not safely proven;
5. guest service duplicate prevention needs adversarial first-insert concurrency proof / DB-invariant review;
6. physical smart-access controller E2E is not verified.

Do not merge or deploy My Stay until these gates are repaired and exact-head tests are green.

## Omnichannel / integrations

Repository contracts exist for Telegram and n8n; outbound/provider evidence is deliberately separated from Core state.

Telegram transport timeout is treated as UNKNOWN rather than automatic success/retry because provider send has no client idempotency key.

Real launch-enabled Telegram/WhatsApp/other providers remain external acceptance items.

## Current gaps

P0 / release:
- real Beget host preflight not performed;
- verified full rollback backup of current live legacy site absent;
- external HTTPS/WSS staging absent;
- 84-room physical production register owner confirmation incomplete;
- real device/provider/browser acceptance absent;
- real external backup/restart/monitoring/restore rehearsal absent;
- production cutover not authorized.

P1:
- stale/unprotected `main`, intentionally deferred until external staging acceptance;
- staff login brute-force protection not demonstrated;
- My Stay branch security/schema/idempotency/CI blockers;
- canonical knowledge required this recovery update.

P2 / target evolution:
- persisted canonical Stay;
- generic tenancy/multi-property isolation model;
- complete Folio/Charge accounting;
- broader Service/Resource engine where proven necessary;
- broader AI controlled-tool ecosystem after deterministic Core capabilities exist.

Deferred / decision-bound:
- NFC;
- statistical forecast claims until adequate historical evidence;
- business rules marked UNKNOWN/DECISION REQUIRED;
- automatic marketing/outbound without explicit governance/consent/provider evidence.

## Deployment

Source/CI:
- integrated RC exact-head workflow contours: VERIFIED;
- CI-local staging/full gate: VERIFIED;
- single-server production package: VERIFIED IN CI;
- Beget compose/preflight/backup/release hardening: VERIFIED IN CI.

External:
- actual Beget host: NOT VERIFIED;
- external HTTPS/WSS staging: NOT VERIFIED;
- live providers/devices: NOT VERIFIED;
- legacy rollback backup: NOT VERIFIED;
- production: NOT READY / NOT EXECUTED / NOT AUTHORIZED.

Current publicly reachable `www.3korony.com` remains the legacy site and is not evidence of the audited Resort OS release.

## P0 release path

Dependency order remains:

1. actual Beget access + non-destructive host preflight;
2. verified full legacy rollback capture;
3. owner-confirm physical 84-room truth;
4. isolated external staging without live DNS cutover;
5. exact migration deployment and staging data reconciliation;
6. external public truth/PMS/staff/browser/mobile/WSS/provider acceptance;
7. backup/restore/restart/monitoring proof;
8. fresh pre-cutover evidence;
9. explicit owner approval for live routing switch;
10. controlled cutover + post-cutover smoke/monitoring;
11. only after accepted external release: promote exact accepted SHA to protected `main` + immutable tag.

## Immediate next task

`RELEASE-P0-EXT-STAGING — Establish real Beget external staging baseline`.

This is the critical path because the application integration is already broad CI-green while production evidence remains external-blocked.

Execution is blocked only by the absence of actual Beget/SSH access in the current connected tool environment. No Beget plugin is installed. Once secure access is available, first action is non-destructive `scripts/host_preflight.sh`; no DNS cutover is implied or authorized.

The 84-room import remains separately blocked by the owner checklist and must not be guessed.

## Extension rule

**EXTEND > REWRITE.**

Preserve and extend rather than rewrite:
- Resort Core authority;
- PostgreSQL inventory constraints;
- human Reservation/payment confirmation;
- PMS V9;
- Payment idempotency;
- AuditLog/RBAC;
- OperationalTask current V1;
- Owner Intelligence / Control / Growth / Executive;
- Guest Services;
- n8n without direct DB authority;
- fail-closed external evidence boundaries.
