# MARINA SMART — Future Luxury 2.0: OWNER Dashboard + PMS visual implementation

**Status:** Draft design implementation, not live production acceptance.

## What is actually implemented

The existing authenticated Admin gets an **appearance-only** Dark/Light toggle whenever Future Luxury is selected. It is stored under a separate local browser key (`marina-fl2-theme`), without sessions, hotel selection, permissions, API calls or database mutations. The legacy appearance remains accessible and unaffected.

The visible, existing OWNER Dashboard has responsive premium cards, metrics, room-state donut and operational rows. Its values continue to arrive via the real `/core/api/v1/admin/dashboard` endpoint. Existing `OwnerExecutivePack`, `OwnerControlV2`, `OwnerOperationsPerformance`, task listings, buttons and navigation remain.

The **actual** PMS grid (`PMSGridV9` → `PMSOwnerGrid`) retains creation, HOLD, opening, edit, pricing and collision checks **exactly as implemented in the server**. Its sticky grid, room status, date headers, reservation bars, filters, legend and the existing booking modal are opt-in restyled. Native booking-bar tooltip still shows its real source/status/dates/payment; no new API or fake values are created.

## Compatibility and visual review

- Dark: navy/teal premium surfaces, full contrast labels and focus rings.
- Light: white/ice surfaces, accessible dark navy text, same booking/status actions.
- Breakpoints: 760px and existing 900/1100px behavior; no change to grid dates, cells or selection.
- Reduced Motion: no required animation; modal entrance suppressed when OS requests it.
- RU/KG/EN and existing KZ locale entries are respected by the active Admin i18n runtime; new appearance labels explicitly translated.
- Approved circular PNG from PR #448 unchanged.

## Gates and limitations

Local static checks cover Auth/RBAC, all 26 Admin tabs, all 30 mobile routes, OWNER sources, i18n and CSS markers. Full Next.js build, screenshots of an **authenticated** actual Dashboard/booking screen on the **new branch**, Android E2E and browser light/dark contrast inspection are separate gates.

No production or DEMO deployment, no API, Prisma, PostgreSQL, booking/business rule modifications. Follow-up remains the next **visual** group only: Reservations/Reception, Guests/CRM, Dining/Finance, then Mobile and staff. Never represent an SVG mockup as deployed functionality.
