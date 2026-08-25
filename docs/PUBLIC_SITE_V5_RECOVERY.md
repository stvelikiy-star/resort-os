# THREE CROWNS — PUBLIC SITE V5 RECOVERY

Date: 2026-08-25
Status: RECOVERED VISUAL BASELINE / SUPERSEDED BY CANONICAL SOURCE WORK

## Vercel evidence

Project: `three-crowns-resort-v5`
Project ID: `prj_6p4U1J07hittPzlJk80hf3DSe03i`
Known production deployment: `dpl_5gsh62bG4tEJmCbdakPwmTweUE9k`
Known alias: `https://three-crowns-resort-v5.vercel.app`

The deployment was fetched again on 2026-08-25 and returned HTTP 200 with title `Три Короны — V5`.

## Recovered design characteristics

V5 established the visual direction used for the canonical rebuild:
- deep green / gold premium palette;
- large lake/pier hero;
- floating booking bar;
- room presentation cards;
- beach/pier section;
- SPA section;
- territory/business section;
- gallery;
- mobile sticky booking CTA.

## Known V5 limitations

The recovered V5 is not a valid production booking implementation:
- booking submit does not call availability API;
- it only validates dates locally and scrolls to room cards;
- category values are simplified `Standard / Suite / Cottage / VIP`, not the actual 12-category inventory;
- room prices are hard-coded display values;
- room selection does not create a request or reservation;
- mobile menu button has no handler;
- branding uses a CSS `III` placeholder rather than the supplied official logo;
- images are hotlinked from the legacy site and third-party sources;
- no canonical Git repository linkage was found for that Vercel project.

## Canonical replacement path

The V5 visual direction is now being recreated in:
`apps/web/`

The canonical site must use:
- `GET /api/v1/booking/check-availability` for real availability/pricing;
- `POST /api/v1/booking/requests` for guest requests;
- actual Three Crowns room categories from Resort Core;
- truthful wording that an unpaid request is not an active reservation.

The existing V5 deployment must remain only a reference/preview until the canonical site passes CI and an explicit deployment/cutover decision is made.
