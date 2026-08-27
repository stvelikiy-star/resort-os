# Three Crowns PMS / CRM / Site Admin — Final Test Baseline

Date: 2026-08-27
Branch: `pms/final-test-20260827`

## Purpose

This branch marks the acceptance baseline for the owner-facing final interactive Resort OS test build. It expands the earlier standalone `/demo` and PALADIN UX reference into the target Three Crowns operating surface while preserving Resort Core as production authority.

The current acceptance artifact is a single offline HTML file with a white / Three Crowns blue visual system, embedded official logo, desktop/mobile navigation and local persistence.

## Test modules

1. Owner dashboard — occupancy, in-house, revenue/night, hot leads, housekeeping, tech blocks, 14-day occupancy, CRM funnel, reception queue, alerts, channel sales.
2. PMS chessboard — 84-room model, 12 canonical categories, 7/14/31-day views, room/category/building/state filters, quick operational slices, room and reservation side panels.
3. Chessboard mutations — future booking drag, conflict preview, date change, planned split, in-stay relocation, immutable lived-night rule, tariff preview without silent total overwrite.
4. CRM — kanban + table, source/search filters, lead card, stage changes, lead → booking conversion.
5. Bookings — reservation/status/payment filters, explicit check-in/check-out, payment recording, cancellation without invented penalty logic.
6. Reception — arrivals, departures, in-house guests, room readiness and NFC handoff surface.
7. Housekeeping — DIRTY → IN_INSPECTION → CLEAN workflow and readiness by building.
8. Maintenance — tickets, TECH_BLOCK, repair completion → IN_INSPECTION.
9. Finance — operational accrued/paid/balance, ADR/RevPAR display, channel revenue, debtor control. Not accounting authority.
10. Analytics — occupancy forecast, channel mix, category performance and owner KPIs.
11. NFC / beach — test UI for bracelet balance, top-up, charge and 5% hotel commission. Production processor remains a later connected contour.
12. Site / content admin — RU/KG/EN guest copy, contacts, SEO, publish state, local persistence and JSON import/export. The offline module is UX acceptance for the target Content API; it does not claim that API is deployed.
13. Reports / RBAC — CSV outputs, daily owner summary and OWNER/MANAGER/MAID/TECHNICIAN/BEACH_PARTNER roles.

## Canonical safety rules preserved

- Resort Core / PostgreSQL remain booking and inventory authority in production.
- Drag/drop never becomes browser-only production truth.
- Schedule mutation follows preview → conflict validation → commit → audit → realtime.
- CHECKED_IN lived nights are immutable; relocation may start today/future only.
- CHECKED_OUT/CANCELLED/NO_SHOW schedules are read-only.
- TECH_BLOCK rooms cannot receive booking moves.
- Schedule changes show current stored total, suggested tariff and delta; they do not silently rewrite commercial value.
- Public booking and PMS use the same inventory truth.
- CMS edits copy/translations/SEO only and cannot write inventory or silently create a reservation.
- Website booking requests remain requests until the approved manager/prepayment workflow confirms a reservation.

## Data note

84 rooms and 12 categories are canonical property-level facts. The standalone final test uses safe demo guests, booking numbers and a demo distribution of physical room codes across the 12 categories until the production room inventory is imported from Resort Core/PostgreSQL.

## Site/PMS integration

The already verified development baseline proves:

`PUBLIC SITE -> CORE AVAILABILITY -> POSTGRESQL`

and:

`PMS ADMIN -> LIVE PMS GRID API -> POSTGRESQL`

The target content-admin path is separately defined by `docs/SITE_ADMIN_CONTENT_CONTRACT.md`:

`ADMIN CONTENT -> CONTENT API -> VERSIONED PUBLISHED CONTENT -> PUBLIC SITE REVALIDATION`

## Standalone acceptance artifact

The handoff file is `three-crowns-resort-os-onefile.html`.

It contains all CSS, JavaScript, official logo and demo data inline; no external stylesheet/script/media dependency is required to open the interface. Test mutations and content edits persist in browser localStorage and can be reset from the top bar.

This branch is intentionally separate from `main` so production authority is not changed by presentation/demo acceptance work.