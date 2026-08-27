# Three Crowns — Unified Site / PMS / CRM / CMS Integration

Date: 2026-08-27
Branch: `integration/site-pms-cms-20260827`

## Goal

Operate the public site, CRM, reservations, PMS chessboard, reception, operations and public-site content from one Resort OS data model without creating competing sources of truth.

## Source-of-truth boundaries

### Booking and inventory truth — Resort Core / PostgreSQL only

Public site availability, room sellability, reservation requests, payments, reservations and PMS inventory blocks remain Core-owned.

Flow:

`PUBLIC SITE -> /booking/check-availability -> Core/PostgreSQL`

`PUBLIC SITE -> /booking/requests -> reservation_requests -> CRM/RequestsBoard`

`MANAGER quote/prepayment confirmation -> booking_admin transaction -> reservations + inventory_blocks`

`reservations/inventory_blocks -> PMSGridV2 -> realtime`

A CMS edit can never create a reservation, block inventory or change availability.

### Public copy truth — versioned CMS document

Public text, contacts and SEO are managed through `site_content_documents`.

Flow:

`OWNER/MANAGER -> Admin / Site Content -> draftJson -> publish -> publishedJson -> public site`

Supported locales: `ru`, `kg`, `en`.

Draft and published versions are separated so unfinished text does not appear publicly.

Every save/publish operation is audited.

## Implemented integration surface

### Core

- `GET /api/v1/site/content?locale=ru|kg|en` — public, published content with safe file fallback.
- `GET /api/v1/admin/site/content` — OWNER/MANAGER editor state.
- `PUT /api/v1/admin/site/content/{locale}/draft` — save draft.
- `POST /api/v1/admin/site/content/{locale}/publish` — publish current draft.
- SQL module `004_site_content.sql` creates versioned content storage.
- `site_content_defaults.json` provides safe RU/KG/EN fallback.

### Admin

- New `Сайт / Контент` tab inside the authenticated Resort OS shell.
- Structured editor for hero, booking, advantages, groups, contacts and SEO.
- Draft/publish states and version visibility.
- JSON import/export for controlled content handoff/backup.
- Blue/white Three Crowns visual override loaded after existing admin styles.

### Public site

- Runtime reads published CMS content through existing `/core` proxy.
- Static site copy remains a graceful fallback when Core is unavailable.
- Server metadata reads published RU SEO with fallback and 60-second revalidation.
- RU/KG/EN header switcher persists selected language.
- Selected language is preserved across internal links.

## Existing production-domain integration reused

This work deliberately reuses existing Core modules instead of duplicating them:

- availability and booking requests in `main.py`;
- quote / prepayment confirmation / conversion in `booking_admin.py`;
- `PMSGridV2` and chessboard mutation contract;
- reception reservations;
- room detail;
- payments/finance;
- operations / staff;
- CRM/inbox/communications;
- realtime WebSocket publication.

## Safety invariants

1. `ReservationRequest` is not a reservation.
2. An unpaid request creates no inventory hold.
3. No global prepayment percentage is inferred by CMS/site UI.
4. PMS mutations use preview/conflict/commit and preserve lived-night history.
5. `TECH_BLOCK` inventory cannot receive a reservation move.
6. Content publishing cannot touch prices, inventory blocks or reservation state.
7. Public site and PMS share Core/PostgreSQL inventory truth.

## Production completion sequence

1. Apply SQL modules including `004_site_content.sql` to the target database.
2. Build/typecheck Core, admin and web from this branch.
3. Smoke test CMS draft/publish with OWNER account.
4. Smoke test public content fallback and DATABASE source.
5. Submit website request and confirm it appears in CRM/requests.
6. Quote and confirm a test prepayment; verify reservation + PMS block.
7. Verify WebSocket refresh across two admin sessions.
8. Verify mobile admin/chessboard explicit actions (no precision-only drag dependency).
9. Deploy preview, complete owner acceptance, then merge/deploy.

## Follow-on enhancements after this integration is accepted

- Expand the CMS schema/editor from the primary commercial blocks to every repeatable public-site card/gallery item.
- Move all visible KG/EN page copy into the same structured CMS document; the current integration establishes the publishing path and primary block translations.
- Add owned media upload/storage management rather than keeping media paths code-owned.
- Add revision history/rollback UI on top of stored audit/version data.
