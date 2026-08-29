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

Exactly **25/25 PR workflow contours** associated with that executable head completed `success`, including Resort Core, Full Staging, Single Server Package, Dependency Security, Migration Baseline, Backup/Restore, PMS Mutation, Realtime, Payments, Guest Services, Owner Intelligence, Owner Control V2, Operations, Inbox, n8n, AI and Public Truth.

Key runs:
- Owner Control V2 CI `33243634765` / job `99077163420`
- Owner Intelligence CI `33243634715`
- Production Migration Baseline CI `33243634644`
- PostgreSQL Backup Restore CI `33243634730`
- Resort Core CI `33243634661`
- Full Staging Gate `33243634787`
- Single Server Package CI `33243634632`

Documentation-only commits after the audited head do not broaden executable verification.

## Current source of truth

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

ReservationRequest remains distinct from Reservation; manager/human confirmation is mandatory. AI/n8n cannot confirm payment or guarantee Reservation. Sheets, n8n, reports, Owner Intelligence and Owner Control do not replace Core/PostgreSQL authority. NFC remains deferred.

## Database

Verified migration chain:
`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots`.

Clean migrate deploy, 84/12 development seed, critical inventory/payment constraints and migration-aware backup -> clean restore are verified.

`owner_analytics_snapshots` is derived management history only: one property/date row, 1..367 day horizon check, object JSON payload, FK and unique protection.

## PMS / Guest Services

PMS V9 is canonical and CI-verified with realtime, server preview/commit, move/resize/Split Stay, conflict/stale protection, TECH_BLOCK protection, CLEAN check-in gate and audit/history.

Guest Services remain Reservation-linked OperationalTasks. Service creation has no automatic accommodation-total or Payment mutation.

## Owner Intelligence

Verified capabilities:
- fail-closed repeat Guest identity resolution;
- Guest directory and reservation/room/payment/service/conversation history;
- 84-room daily heatmap;
- period comparisons;
- CSV / browser print;
- real XLSX export with `Итоги`, `Занятость по номерам`, `Брони`, `Гости`, `Платежи`.

Management figures are not statutory accounting.

## Owner Control V2

Verified capabilities:
- 7/30-day forward on-books occupancy;
- booked/available rooms by day;
- management allocated booked value;
- arrivals/departures;
- factual repeat-Guest segments;
- Action Center: not-ready arrivals, unassigned 72h, debt 72h, urgent tasks, messages needing reply, Guest duplicates;
- one hotel-local-date snapshot with AuditLog;
- OWNER/MANAGER and service-auth capture;
- real net booking pickup from stored prior snapshots;
- `INSUFFICIENT_HISTORY` / `INSUFFICIENT_COVERAGE` fail-closed states;
- no fabricated past and no statistical forecast claim.

Daily n8n snapshot template: 03:10 Asia/Bishkek, 180-day horizon, Core service-auth only, no direct DB write. Repository template remains inactive; live scheduler execution is NOT VERIFIED.

## Public / channels / AI / staff

Public truth guards remain green. Operations/Staff, Inbox, Telegram, AI Sales Draft, AI Administrator and n8n contracts remain green on the audited head. Real devices and live external providers remain NOT VERIFIED.

Approved channels remain Instagram -> ManyChat -> n8n; WhatsApp -> API Green -> n8n; website -> Core; Sheets mirror/control only.

## Current gaps

- distinct persisted Stay not implemented;
- generic multi-property tenancy not implemented;
- complete Folio/Charge accounting not implemented;
- statistical forecast deferred until enough clean historical data and measurable accuracy;
- NFC deferred;
- physical production 84-room register not owner-confirmed.

## Deployment state

- CI-local staging: VERIFIED (`33243634787`).
- Single-server package: VERIFIED IN CI (`33243634632`).
- Beget direction: approved; actual host capability NOT VERIFIED.
- Rollback backup: BLOCKED / NOT VERIFIED.
- External HTTPS/WSS staging: BLOCKED / NOT VERIFIED.
- Live providers/devices: BLOCKED / NOT VERIFIED.
- Production cutover: NOT PRODUCTION READY / NOT EXECUTED.

## P0 release path

Beget access/preflight -> verified rollback backup -> isolated external staging -> activate/observe daily snapshots -> external public-truth/browser/device/provider acceptance -> fresh cutover evidence.

## Non-blocked P1 work

Continue without weakening P0 boundaries:
- controlled post-stay feedback/NPS/review;
- controlled repeat-Guest follow-up/reactivation;
- safe historical Guest duplicate resolution if required;
- monitoring/restore templates;
- attribution/control.

## Extension rule

Extend rather than rewrite Resort Core authority, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9 preview/commit, Owner Intelligence, Owner Control derived history, Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask and n8n-without-DB-authority.
