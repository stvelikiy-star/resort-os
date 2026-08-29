# RESORT OS — CURRENT STATE

Version: 2.5
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL STAGING VERIFIED / PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository `stvelikiy-star/resort-os`, branch `integration/site-pms-cms-20260827`, PR #37.

LAST AUDITED EXECUTABLE HEAD: `f656dc5f365550d1a8101cbaba99c3bbeb645a6b`
LAST AUDITED: 2026-08-29

All **26/26 PR workflow contours** associated with that exact executable head completed `success`.

Key evidence:
- Owner Growth Control CI `33244775546`, job `99080256833`
- Owner Control V2 CI `33244775528`
- Owner Intelligence CI `33244775506`
- Production Migration Baseline CI `33244775486`
- PostgreSQL Backup Restore CI `33244775492`
- Resort Core CI `33244775516`
- Full Staging Gate `33244775521`
- Single Server Package CI `33244775501`
- PMS Mutation `33244775505`
- Realtime PMS `33244775498`
- Payment Idempotency `33244775468`
- Guest Services `33244775508`
- Public Site Truth `33244775483`
- Dependency Security `33244775469`
- Unified Inbox `33244775517`
- Hotel Operations `33244775490`
- Control Center Contract `33244775478`
- AI Administrator `33244775511`
- AI Sales Draft `33244775496`
- n8n Resort Core Contract `33244775481`
- n8n Workflow JSON `33244775530`
- Automation Contract `33244775485`
- Data Intake Integrity `33244775489`
- Staff Voice `33244775529`
- Telegram Sales `33244775466`
- NFC Deferred Scope `33244775482`

Documentation-only commits after the audited head do not broaden executable verification. The exact audited executable head remains the evidence boundary until another executable head receives equivalent verification.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

ReservationRequest != Reservation. Human manager confirmation is mandatory. AI/n8n cannot confirm payment or guarantee Reservation. Sheets, n8n, reports, management snapshots and Growth queues are not parallel booking/payment truth. NFC remains deferred.

## Database

Verified migration chain:
`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements`.

Clean deployment, exact five-migration ledger, 84/12 development seed, critical inventory/payment invariants, Growth persistence constraints and backup -> clean restore are verified.

`owner_analytics_snapshots` stores derived management snapshots only. `guest_engagements` stores internal manager follow-up and factual feedback only. Neither replaces Reservations, InventoryBlocks, Payments or communication provider truth.

## PMS / services

PMS V9 remains canonical with realtime, server preview/commit, move/resize/Split Stay, stale/conflict protection, TECH_BLOCK protection, CLEAN check-in gate and audit history.

Guest Services are Reservation-linked OperationalTasks and do not automatically mutate accommodation total or create Payment.

## Owner Intelligence

Verified: repeat-Guest fail-closed identity, Guest history, room/payment/service/conversation drill-down, 84-room heatmap, period comparison, CSV/print and real XLSX export. Management metrics are not statutory accounting.

## Owner Control V2

Verified:
- 7/30-day factual forward on-books view;
- daily occupancy/capacity/value/arrivals/departures;
- Action Center for not-ready arrivals, unassigned rooms, debt, urgent tasks, replies and Guest duplicates;
- one hotel-local-date snapshot;
- manual and service-auth capture;
- real snapshot-based net booking pickup;
- fail-closed `INSUFFICIENT_HISTORY` / `INSUFFICIENT_COVERAGE`;
- no fabricated historical values and no statistical forecast claim.

n8n snapshot template is configured for 03:10 Asia/Bishkek, 180 days, service-auth Core only and no DB write. It remains inactive in repository; live scheduling is NOT VERIFIED.

## Owner Growth Control

STATUS: **IMPLEMENTED AND CI-VERIFIED ON THE AUDITED EXECUTABLE HEAD.**

Current management surface: `Рост / Отзывы`.

Verified Growth capabilities:
- internal engagement queue for `POST_STAY_FEEDBACK`, `RETURN_GUEST`, `MANAGER_FOLLOWUP`;
- statuses `OPEN`, `IN_PROGRESS`, `DONE`, `CANCELLED`;
- post-stay candidates only from completed `CHECKED_OUT` stays with available contact and no existing feedback engagement;
- reactivation candidates only from factual past stay history, no active future stay and no active RETURN_GUEST task;
- linked Reservation must belong to the same primary Guest/property;
- one POST_STAY_FEEDBACK engagement per Reservation;
- active RETURN_GUEST duplicate protection;
- RETURN_GUEST rejected when an active future Reservation exists;
- factual feedback score 0-10;
- standard NPS classification 0-6 detractor / 7-8 passive / 9-10 promoter;
- NPS always exposes sample size;
- detractor feedback remains `IN_PROGRESS` as recovery work until a manager completes it;
- summary exposes active/overdue queue, feedback queue, return queue, recovery, average score, promoters/passives/detractors and factual candidate counts;
- AuditLog covers engagement creation, status change and feedback recording;
- property isolation is verified;
- database constraints reject invalid kind/status/score combinations;
- admin UI typecheck and production build are verified.

Governance boundary:
- `outbound_authority = NONE_AUTOMATIC`;
- Growth routes contain no send/outbound endpoint;
- a candidate is not marketing consent;
- creating a Growth task does not send a message;
- no AI propensity/VIP score is assigned;
- Reservation/payment authority is unchanged.

Dedicated evidence: Owner Growth Control CI `33244775546`, job `99080256833`, conclusion `success`.

## Other current contours

Public truth, Operations/Staff, Inbox, Telegram, n8n contracts, AI Sales Draft and AI Administrator remain CI-green on the same executable head. Live external providers and real devices remain NOT VERIFIED.

## Current gaps

Persisted Stay, generic tenancy and complete Folio/Charge accounting are not implemented. Statistical forecasting is deferred until clean historical snapshot data is sufficient and accuracy can be measured. Growth has no automatic outbound authority. Production physical room register remains unconfirmed. NFC is deferred.

## Deployment

- CI-local staging: VERIFIED (`33244775521`).
- Single-server package: VERIFIED IN CI (`33244775501`).
- Beget direction approved; actual host capability NOT VERIFIED.
- Rollback backup of current live legacy site NOT VERIFIED.
- External HTTPS/WSS staging NOT VERIFIED.
- Live providers/devices NOT VERIFIED.
- Production NOT READY / NOT EXECUTED.

## P0 release path

Beget preflight -> verified rollback backup -> isolated external staging -> activate/observe daily snapshots only after deployment approval -> external truth/browser/device/provider acceptance -> fresh cutover evidence.

## Non-blocked P1

Next safe product work may extend owner monthly/weekly management reporting, reputation/recovery reporting, monitoring/restore templates, attribution, and optionally a governed manual outbound handoff. Automatic marketing outreach must not be introduced without explicit consent/governance/provider verification.

## Extension rule

Extend rather than rewrite Resort Core, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9, Owner Intelligence, Owner Control, Owner Growth Control, Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask and n8n-without-DB-authority.
