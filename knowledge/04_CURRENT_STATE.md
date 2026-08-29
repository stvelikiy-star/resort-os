# RESORT OS — CURRENT STATE

Version: 2.6
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL STAGING VERIFIED / PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository `stvelikiy-star/resort-os`, branch `integration/site-pms-cms-20260827`, PR #37.

LAST AUDITED EXECUTABLE HEAD: `1be110c35e1e7d5876cae40a1b58cef42bd10a22`
LAST AUDITED: 2026-08-29

All **26/26 PR workflow contours** associated with that exact executable head completed `success`.

Key evidence on the audited head:
- Owner Growth Control CI `33245328533`
- Owner Control V2 CI `33245328508`
- Owner Intelligence CI `33245328544`
- Production Migration Baseline CI `33245328548`
- PostgreSQL Backup Restore CI `33245328550`
- Resort Core CI `33245328528`
- Full Staging Gate `33245328535`
- Single Server Package CI `33245328529`
- PMS Chessboard Mutation CI `33245328512`
- Realtime PMS CI `33245328538`
- Payment Idempotency CI `33245328520`
- Guest Services PMS CI `33245328498`
- Public Site Truth CI `33245328516`
- Dependency Security `33245328532`
- Unified Inbox CI `33245328518`
- Hotel Operations CI `33245328499`
- Control Center Contract CI `33245328536`
- AI Administrator CI `33245328564`
- AI Sales Draft CI `33245328545`
- n8n Resort Core Contract CI `33245328514`
- n8n Workflow JSON CI `33245328523`
- Automation Contract CI `33245328527`
- Data Intake Integrity CI `33245328525`
- Staff Voice CI `33245328540`
- Telegram Sales CI `33245328543`
- NFC Deferred Scope CI `33245328521`

Documentation-only commits after the audited head do not broaden executable verification. The exact audited executable head remains the evidence boundary until a later executable head receives equivalent verification.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

ReservationRequest != Reservation. Human manager confirmation is mandatory. AI/n8n cannot confirm payment or guarantee Reservation. Sheets, reports, management snapshots, Growth queues and Executive Pack are read/control surfaces, not parallel booking/payment truth. NFC remains deferred.

## Database

Verified migration chain:
`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements`.

Clean deployment, exact five-migration ledger, 84/12 development seed, critical inventory/payment invariants, Growth constraints and backup -> clean restore are verified.

`owner_analytics_snapshots` stores derived management snapshots only. `guest_engagements` stores internal manager follow-up and factual feedback only. Neither replaces Reservations, InventoryBlocks, Payments or provider truth.

## PMS / Guest Services

PMS V9 remains canonical with realtime, server preview/commit, move/resize/Split Stay, stale/conflict protection, TECH_BLOCK protection, CLEAN check-in gate and audit history.

Guest Services are Reservation-linked OperationalTasks and do not automatically mutate accommodation total or create Payment.

## Owner Intelligence

Verified: repeat-Guest fail-closed identity, complete Guest history, room/payment/service/conversation drill-down, 84-room heatmap, period comparison, CSV/print and real XLSX export. These are management metrics, not statutory accounting.

## Owner Control V2

Verified:
- 7/30-day factual forward on-books view;
- daily occupancy/capacity/value/arrivals/departures;
- Action Center for not-ready arrivals, unassigned rooms, debt, urgent tasks, replies and Guest duplicates;
- hotel-local analytics snapshots;
- manual and service-auth snapshot capture;
- real snapshot-based net booking pickup;
- fail-closed `INSUFFICIENT_HISTORY` / `INSUFFICIENT_COVERAGE`;
- no fabricated historical values and no statistical demand forecast claim.

Repository n8n snapshot workflow is configured for 03:10 Asia/Bishkek, 180 days, Core service-auth only, no direct DB write and remains inactive in repository. Live deployed scheduling is NOT VERIFIED.

## Owner Growth Control

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Current management surface: `Рост / Отзывы`.

Verified:
- internal queue for `POST_STAY_FEEDBACK`, `RETURN_GUEST`, `MANAGER_FOLLOWUP`;
- OPEN / IN_PROGRESS / DONE / CANCELLED;
- factual post-stay and reactivation candidate selection;
- Reservation/Guest/property consistency;
- duplicate feedback and active return protection;
- RETURN_GUEST rejected when an active future Reservation exists;
- factual score 0–10;
- NPS: 0–6 detractor, 7–8 passive, 9–10 promoter;
- NPS always exposes sample size;
- detractor remains recovery work until manager completion;
- AuditLog and property isolation;
- DB constraints and production admin build.

Governance boundary: `outbound_authority = NONE_AUTOMATIC`. Growth contains no send/outbound endpoint. Candidate != marketing consent. No AI propensity/VIP score. Reservation/payment authority is unchanged.

## Owner Executive Pack

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

The Command Center now contains a single owner summary composed from already verified Resort Core read models. It introduces no persistence table and no second calculation source.

Verified surface includes:
- current month-to-date occupancy;
- MTD ADR and RevPAR;
- MTD recorded payments;
- MTD CRM conversion;
- comparison against the comparable beginning of the previous month, capped at previous-month end when that month is shorter;
- current active outstanding/debtor count;
- next-30-day on-books occupancy, booked room nights, available room nights, allocated booked value, arrivals and departures;
- booking pickup only when a stored prior snapshot makes it factual; otherwise `—` / readiness status;
- factual NPS, sample size and average score;
- recovery count;
- return-Guest candidates and active return queue;
- Owner Control CRITICAL/HIGH action facts and overdue Growth work;
- browser print/PDF;
- explicit truth boundary explaining management metrics vs accounting and on-books vs forecast.

Evidence on exact head `1be110c35e1e7d5876cae40a1b58cef42bd10a22`:
- Owner Growth Control CI production admin typecheck/build — success;
- Resort Core CI PMS admin/public/staff builds plus full Core lifecycle — success;
- Full Staging Gate real application container build/start and complete staging acceptance — success;
- Single Server Production Package CI deterministic application-image build — success;
- all other 22 associated PR contours — success.

Executive Pack is a read/composition layer only. It does not create Reservation, Payment, GuestEngagement, snapshot or communication records.

## Other current contours

Public truth, Operations/Staff, Inbox, Telegram, n8n contracts, AI Sales Draft and AI Administrator are CI-green on the audited head. Live external providers and real devices remain NOT VERIFIED.

## Current gaps

Persisted canonical Stay, generic tenancy and complete Folio/Charge accounting are not implemented. Statistical forecasting remains deferred until clean historical snapshot data is sufficient and accuracy can be measured. Growth has no automatic outbound authority. Production physical room register remains unconfirmed. NFC is deferred.

## Deployment

- CI-local staging: VERIFIED (`33245328535`).
- Single-server package: VERIFIED IN CI (`33245328529`).
- Beget direction approved; actual host capability NOT VERIFIED.
- Rollback backup of exact current live legacy site NOT VERIFIED.
- External HTTPS/WSS staging NOT VERIFIED.
- Live providers/devices NOT VERIFIED.
- Production NOT READY / NOT EXECUTED.

## P0 release path

Beget preflight -> verified rollback backup -> isolated external staging -> external truth/browser/device/provider acceptance -> fresh backup/preflight/secrets/DNS rollback evidence -> explicit owner cutover approval.

## Non-blocked P1

Safe next work may extend owner weekly/monthly reporting, reputation/recovery analytics, monitoring/restore templates and attribution. Automatic marketing outreach must not be introduced without explicit consent/governance/provider verification.

## Extension rule

Extend rather than rewrite Resort Core, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9, Owner Intelligence, Owner Control, Owner Growth Control, Owner Executive Pack, Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask and n8n-without-DB-authority.
