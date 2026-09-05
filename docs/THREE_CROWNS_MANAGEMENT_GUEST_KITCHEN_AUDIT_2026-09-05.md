# Three Crowns — Management / Kitchen / Guest OS audit

Date: 2026-09-05
Branch: `ux/management-kitchen-guest-v1-20260905`
Base: `integration/site-pms-cms-20260827`
Status: implementation branch / not production

## Goal

Finish the current management system without replacing Resort Core boundaries; give Kitchen/Dining a direct operational entry; turn Guest OS into a useful in-stay concierge and controlled commercial surface without allowing frontend/AI to become transaction truth.

## Confirmed defects and gaps

### Admin dashboard

A late `admin-experience.css` selector forced nearly every descendant of `.dashboard-shell` to white text. Owner Control V2 contains light cards, so this produced white-on-light content that looked like empty silhouettes. Semantic room-state cards had the same contrast problem.

Fix on this branch: narrow the blue/white override to Command Center cards; explicitly preserve Owner Executive and Owner Control palettes; keep semantic room-state cards readable.

### Reception

Core correctly blocks CHECK_IN until the assigned room is `CLEAN`, but Reception currently explains the failure without giving a direct operational handoff. This is an UX gap, not a reason to weaken the Core check-in rule.

Next controlled change: add a clear readiness status and manager/reception-safe handoff into housekeeping without giving RECEPTION unrestricted Operations permissions.

### Kitchen / Dining

Current Core already has:
- Kitchen menu items;
- tables and table statuses;
- server-derived orders;
- order lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- Guest OS kitchen order endpoint;
- check-in arrival cards for Dining;
- no automatic Hotel Payment / Reservation total mutation.

Gaps found:
- `/kitchen` had no dedicated direct sign-in experience;
- no concise "today" pulse before the operational tabs;
- DINING_STAFF currently combines floor/waiter and kitchen permissions; UI separation can improve before introducing new roles;
- menu has active/draft but no real calendar/service-window/sold-out model, so "menu today" cannot yet truthfully mean a scheduled daily menu;
- the legacy guest kitchen menu endpoint exposes active draft rows because it checks `isActive` but not `isDraft`.

Implemented on this branch:
- dedicated `/kitchen` entry using existing Core auth and existing OWNER/MANAGER/DINING_STAFF permissions;
- live kitchen pulse for orders, tables, published-vs-draft menu and arrivals;
- new fail-closed guest Marketplace endpoints that expose/order only active non-draft menu items.

### Guest OS

Current Guest OS already has QR+PIN session authority, RU/KG/EN, service requests and status tracking. It lacked a real Kitchen menu/order presentation and a structured in-stay offer surface. Its old MEALS quick form also uses a static extra-meal estimate instead of the newer Kitchen catalogue.

Implemented on this branch:
- premium Guest Marketplace surface;
- live Kitchen menu presentation with quantities, guest count, notes and order total;
- Core-backed room order creation;
- controlled offer hooks for transfer, sauna, excursions, billiards and administrator assistance; offers create requests, never automatic commercial confirmation;
- guest-oriented AI concierge UI using the existing fail-closed AI endpoint;
- optional `NEXT_PUBLIC_KOL_MARKETPLACE_URL` bridge. It appears only when configured; no KÖL URL or partner promise is fabricated.

## Non-negotiable boundaries

- Resort Core/PostgreSQL remain transaction truth.
- AI cannot confirm a Reservation, payment, discount, provider availability or invented hotel fact.
- Kitchen order totals do not post Hotel Payment automatically.
- Guest Marketplace must never publish draft menu rows.
- KÖL is an optional configured external bridge, not Resort OS transaction truth.
- NFC/wallet and real payment-lock work remain deferred and are not reactivated by this branch.
- Beget/DNS/production cutover remains STOP.

## Remaining delivery order

1. Compile/build/contract CI on the branch and fix actual failures.
2. Switch Guest Marketplace UI to the new fail-closed Marketplace menu/order endpoints before merge.
3. Reception readiness UX and safe housekeeping handoff.
4. Management module-by-module UX pass: Dashboard -> PMS -> Reception -> Guest/Services -> Operations -> Finance/Reports -> Staff/Kitchen -> Inbox/Content.
5. Kitchen V2 decision: daily service windows/sold-out, new menu-item creation, and whether WAITER and KITCHEN need separate roles or only separate views.
6. Guest Marketplace V2: owner-configurable offers, impression/click/request analytics, stay-aware AI context with the same permission/truth boundary.
7. Only after internal acceptance: preview deployment and device/browser review. Production remains separate.
