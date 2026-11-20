# MARINA SMART — OWNER Command Center Future Luxury visual pilot

**Scope:** authenticated Admin `DashboardBoard` only, and only when `html[data-marina-ui="future-luxury"]` and `data-fl2-owner="true"`.

## What changes

- Premium navy/cyan/champagne Command Center header treatment and accessible refresh action.
- Compact dark KPI tiles with tabular numerals, semantic labels and lightweight finite reveal.
- Responsive 155px/185px min grid (depending on viewport); labels and financial values wrap rather than disappear.
- Clear keyboard focus, disabled motion for `prefers-reduced-motion: reduce`.

## What remains unchanged

- Fetch and refresh call `/core/api/v1/admin/dashboard` and all Core payload data/identity.
- Dashboard earnings in som, arrivals, departures, active requests, communications, room readiness.
- `OwnerExecutivePack`, `OwnerControlV2`, `OwnerOperationsPerformance` and the rest of the render tree.
- Permission/isOwner decision, navigation callbacks, error and loading states, other Admin tabs, all Staff and Expo screens.
- Existing legacy appearance remains the default; opt-in Future Luxury can be toggled back.

## Acceptance gate

Local static source guard `npm run design:fl2:owner` and base functional, accessibility, icon and locale checks must all pass. Inspect browser screenshots in Legacy/Future Luxury at 320/375/768/1440px; test keyboard-only access and Reduced Motion. Then verify all OWNER actions against a real staging Core API before acceptance.

**Visual QA NOT VERIFIED; LIVE NOT VERIFIED; Android E2E NOT VERIFIED.** No deployment or merge until CI and the user review.
