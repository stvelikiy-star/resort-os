# Three Crowns Resort OS — Management Final Acceptance

Date: 2026-09-06
Scope: management/admin/staff/Resort Core only
Public website: FROZEN by owner instruction; no public website changes are part of this acceptance.

## Accepted management contour

The working management contour is treated as one Resort Core-backed system:

- Owner/Manager dashboard and operational intelligence;
- PMS / Super Chessboard with reservation mutations and database-level overlap protection;
- Rates / Seasons with manager-controlled periods, overlap rejection and audit history;
- CRM / reservation requests and manager-confirmed reservation/payment workflow;
- Reception, arrivals/departures, folio visibility and room-readiness handoff;
- Guest Services Center with OWNER/MANAGER/RECEPTION RBAC;
- Housekeeping and maintenance tasks, assignment, status transitions and history;
- internal hotel finance, receivables and exception control;
- reports / analytics / owner intelligence;
- staff accounts and access control, including role changes, password rotation, disable/enable and session revocation;
- Dining / Kitchen order lifecycle and table operations;
- production Kitchen menu catalogue: OWNER/MANAGER create/edit/publish; DINING_STAFF cannot mutate catalogue price/publication;
- room QR / service-point QR operational control under existing safe boundaries;
- unified Inbox with inbound idempotency, needs-reply, claiming, internal notes, outbound capability truth and AI capability truth;
- Guest offer campaign management and click/request analytics already available in Admin.

## Acceptance evidence

The final management acceptance is not based on UI presence alone. The repository contains domain and release gates for:

- Resort Core schema/build/E2E;
- PMS final acceptance and chessboard mutation;
- Reception RBAC;
- Management Control (rates/seasons and staff access);
- Hotel Operations;
- Finance Control;
- Guest Services Center;
- Kitchen Operations and Kitchen Menu Management;
- Dining realtime/folio/coordination/production snapshots;
- Unified Inbox;
- Guest OS request/access/PIN contracts;
- Service Point QR;
- payment idempotency;
- PostgreSQL backup/restore;
- n8n/automation contracts;
- dependency security;
- Full Staging Gate;
- Resort OS Release Gate.

A separate `verify_management_final_acceptance.py` guard performs more than 70 final static truth assertions across the runtime composition, RBAC boundaries, production UIs and executable CI gates.

## Non-negotiable truth boundaries

- PostgreSQL/Resort Core remain transaction truth.
- Website files are outside this management completion and remain unchanged.
- AI/n8n do not directly confirm payment, reservation, discounts, provider availability or invented hotel facts.
- Kitchen orders do not automatically create Hotel Payment records.
- Changing a current tariff does not silently rewrite totals of existing reservations.
- DINING_STAFF does not control catalogue price/publication.
- Reception cannot bypass room-readiness rules for check-in.
- NFC legacy wallet/acquiring remains deferred and is not part of active V1.
- Bank/TTLock production activation remains separate until real provider/API credentials and an approved production cutover exist.

## Deliberately not changed

The public website (`apps/web/**`) is owner-frozen. Public/guest-facing enhancements that would require modifying that surface are not blockers for management acceptance and are not introduced by this closure.

## Final delivery definition

Management is accepted as ready for owner/staff use when:

1. this branch contains no `apps/web/**` diff;
2. the final truth guard passes;
3. Admin and Staff applications typecheck/build;
4. Python Core/acceptance scripts compile;
5. all triggered repository CI, especially Management Control, Kitchen, Guest Services, Inbox, Full Staging and Release Gate, are green.

Production infrastructure cutover is a separate deployment operation, not a missing management feature.
