# Three Crowns Site Admin / Content Integration Contract

Date: 2026-08-27
Status: TARGET IMPLEMENTATION CONTRACT

## Goal

The public site, PMS, CRM and content administration must be one system, not independent sources of truth.

Authoritative boundaries:

- room availability, reservations, room assignments and booking state: Resort Core + PostgreSQL;
- PMS chessboard mutations: Resort Core preview/commit contract;
- website copy, translations, contact text, SEO and publish state: Site Content API;
- incoming website booking requests: existing Core booking-request flow, surfaced in CRM;
- room category identity/pricing: canonical Core catalog, not duplicated in CMS.

## Required data flow

`PUBLIC SITE -> /core availability -> RESORT CORE -> POSTGRESQL`

`PUBLIC SITE -> booking request -> CORE -> CRM queue`

`ADMIN SITE CONTENT -> CONTENT API -> versioned content store -> PUBLIC SITE revalidation`

`PMS CHESSBOARD -> preview/commit -> CORE -> POSTGRESQL -> WebSocket -> all PMS clients`

The CMS must never write inventory blocks or create an active reservation.

## Content document

A published content document contains:

- `status`: DRAFT | READY | PUBLISHED;
- `updated_at`, `updated_by`;
- shared contact block: booking phone, manager WhatsApp, email, address;
- localized objects for `ru`, `kg`, `en`;
- per-language hero title/text;
- booking-section title/text;
- rooms-section title/text;
- territory text;
- group/sports text;
- reviews heading/introduction;
- contacts heading/text;
- SEO title/description;
- optional media references by stable media key.

Room category code/name/capacity/area/rate are not free-text CMS data. They are resolved from the canonical room catalog/Core.

## Target API

Read public content:

`GET /api/v1/content/public?locale=ru`

Admin draft:

`GET /api/v1/admin/content`

`PUT /api/v1/admin/content`

Publish:

`POST /api/v1/admin/content/publish`

History/audit:

`GET /api/v1/admin/content/versions`

Every admin write requires authenticated OWNER or MANAGER permission and writes AuditLog.

## Publish behavior

1. Manager edits RU/KG/EN content in admin.
2. Draft is validated server-side.
3. Publish creates an immutable version snapshot.
4. Public content pointer advances atomically to the new version.
5. Public Next.js site is revalidated.
6. Previous published version remains available for rollback.

Publishing content does not change room availability, pricing truth, booking state or payment state.

## CRM link

Website booking requests remain ReservationRequest/non-reservation until manager confirmation and the approved prepayment flow. Each request must be queryable in CRM with source `SITE`, guest contacts, dates, party size and request status.

A CRM action may open availability and create/confirm a reservation only through the approved Core transaction. No CMS action performs that conversion.

## Offline acceptance UI

The standalone one-file PMS/CRM acceptance artifact includes a `Сайт / контент` module with RU/KG/EN editing, contact/SEO fields, local persistence and JSON import/export. That module is an offline UX acceptance surface; it does not claim production Content API is deployed.

## Production acceptance criteria

- content changes require OWNER/MANAGER authentication;
- RU/KG/EN validation prevents missing required public strings;
- versioned publish + rollback exists;
- audit entry exists for every content mutation/publish;
- public site reads published content only;
- PMS/site still share Core inventory truth;
- site request appears in CRM without becoming a reservation automatically;
- public site can be revalidated after publish without a full manual redeploy.
