# MARINA SMART Mobile — Restaurant P0, isolated implementation

Base: `7c23fbd479dcc6f8c90b1fa5fbd05688315e5f93`  
Change scope: **apps/mobile only**. Do not deploy to ASKA_TASH or change Ubuntu, database, API, design, MARINA AI, or WhatsApp from this branch.

## Implemented from existing Core endpoints

| Mobile action | Verified Core route | Important rule |
| --- | --- | --- |
| List current seatings | GET `/api/v1/dining/sessions?status=ACTIVE` | Property-local current date; server-scoped |
| Select eligible guest from stays | GET `/api/v1/dining/stays` | Only verified stay identities, no invented guests |
| Seat guest at free table | POST `/api/v1/dining/sessions` | Server enforces stay/table availability, party size, role |
| Confirm waiting seating | PATCH `/api/v1/dining/sessions/{id}/status` | WAITING → SEATED |
| Move guests | POST `/api/v1/dining/sessions/{id}/move` | Existing reservations/conflicts checked by Core, waiter assignment KEEP |
| Finish seating | PATCH `/api/v1/dining/sessions/{id}/status` | SEATED → RELEASED; table goes to CLEANING, **not directly AVAILABLE** |
| List chargeable orders | GET `/api/v1/dining/folio-orders` | WAITER sees own assigned orders |
| Post room folio charge | POST `/api/v1/dining/orders/{id}/folio` | **Creates OPEN folio charge, not Payment** |

Existing table creation, kitchen order entry, menu selection and kitchen status flows remain intact.

Mutation responses are validated against expected record IDs/status. Non-GET failures are not automatically retried. Operations are journaled under the authenticated hotel/user before sending; an unknown outcome blocks subsequent dining writes until operator manually reviews the result in Web.

## Server limitation confirmed — do not fake a mobile success

The existing `PATCH /api/v1/kitchen/orders/{id}/status` only allows WAITER → SERVED through `shared_dining_staging_guard()`, which explicitly refuses the production/legacy hotel mode. A production-grade waiter **serve** action therefore still needs a separately reviewed Core authorization contract. No bypass was added.

Also outstanding: menu-day publication for OWNER/MANAGER, owner/manager kitchen navigation, proper staff mobile actions, Android physical-device acceptance. These are later approved plan stages and are **not** silently claimed as completed.

## Release gates

1. CI typecheck, lint, Jest, backend route verification, Android preview on exact PR SHA.
2. Isolated database E2E with WAITER/COOK/OWNER/MANAGER, verifying authentic stay and room-folio persistence, server-generated 403/409, and no invented Payment.
3. Physical Android: seat guest → create table order → kitchen READY → room folio → transfer table → release after service; verify WEB/PMS on same PostgreSQL.
4. Server-side serving contract resolved without unapproved privilege changes.
5. UX review / localization RU/KG/EN; reconcile layout with Future Luxury separately.

**PR remains Draft until gates are passed.**
