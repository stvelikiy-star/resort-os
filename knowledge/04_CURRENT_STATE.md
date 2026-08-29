# RESORT OS — CURRENT STATE

Version: 2.4
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL STAGING VERIFIED / PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## Audited executable boundary

Repository `stvelikiy-star/resort-os`, branch `integration/site-pms-cms-20260827`, PR #37.

LAST AUDITED EXECUTABLE HEAD: `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`
LAST AUDITED: 2026-08-29

All **25/25 PR workflow contours** associated with that exact executable head completed `success`.

Key evidence:
- Owner Control V2 CI `33243634765`, job `99077163420`
- Owner Intelligence CI `33243634715`
- Production Migration Baseline CI `33243634644`
- PostgreSQL Backup Restore CI `33243634730`
- Resort Core CI `33243634661`
- Full Staging Gate `33243634787`
- Single Server Package CI `33243634632`
- PMS Mutation `33243634705`
- Realtime PMS `33243634714`
- Payment Idempotency `33243634700`
- Guest Services `33243634701`
- Public Site Truth `33243634710`
- Dependency Security `33243634667`
- Unified Inbox `33243634654`
- Hotel Operations `33243634721`

Documentation-only commits after the audited head do not broaden executable verification.

## Authority

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

ReservationRequest != Reservation. Human manager confirmation is mandatory. AI/n8n cannot confirm payment or guarantee Reservation. Sheets, n8n, reports and management snapshots are not parallel truth. NFC remains deferred.

## Database

Verified migration chain:
`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots`.

Clean deployment, 84/12 development seed, critical inventory/payment invariants and backup -> clean restore are verified.

Owner analytics snapshots are derived management evidence: one property/date row, validated horizon/payload and AuditLog capture. They do not replace Reservations/InventoryBlocks/Payments.

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

## Other current contours

Public truth, Operations/Staff, Inbox, Telegram, n8n contracts, AI Sales Draft and AI Administrator remain CI-green. Live external providers and real devices remain NOT VERIFIED.

## Current gaps

Persisted Stay, generic tenancy and complete Folio/Charge accounting are not implemented. Statistical forecasting is deferred until clean historical data is sufficient and accuracy can be measured. Production physical room register remains unconfirmed. NFC is deferred.

## Deployment

- CI-local staging: VERIFIED (`33243634787`).
- Single-server package: VERIFIED IN CI (`33243634632`).
- Beget direction approved; actual host capability NOT VERIFIED.
- Rollback backup NOT VERIFIED.
- External HTTPS/WSS staging NOT VERIFIED.
- Live providers/devices NOT VERIFIED.
- Production NOT READY / NOT EXECUTED.

## P0 release path

Beget preflight -> verified rollback backup -> isolated external staging -> activate/observe daily snapshots -> external truth/browser/device/provider acceptance -> fresh cutover evidence.

## Non-blocked P1

Controlled post-stay feedback/NPS/review, repeat-Guest follow-up/reactivation, optional safe historical Guest duplicate resolution, monitoring/restore templates and attribution can continue without granting automatic outbound or booking authority.

## Extension rule

Extend rather than rewrite Resort Core, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9, Owner Intelligence, Owner Control, Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask and n8n-without-DB-authority.
