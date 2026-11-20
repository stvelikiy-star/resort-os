# Future Luxury web shell rollout

Phase one is an optional authenticated Admin shell skin. Legacy remains the default. Staff can
switch between **Legacy** and **Future Luxury** beside **Выйти**; the browser stores only that
visual preference in `localStorage` under `marina-admin-ui`. No preference is sent to an API.

The premium scope is `html[data-marina-ui="future-luxury"]` and is intentionally limited to the
top bar, identity, navigation, overflow menu, appearance control and logout control. Operational
content—including tables, calendars, dashboards and finance cards—retains its existing palette.
The logo is unchanged while the canonical transparent PNG master remains unverified.

Before making the skin default, visually QA OWNER, MANAGER, RECEPTION, AGENT, MAID and TECHNICIAN
access at desktop, tablet and narrow mobile widths. Verify keyboard focus, contrast, overflow-menu
reachability, reduced motion, all 26 navigation destinations, module enablement gates, empty grants,
long hotel/user names and browser storage-disabled behavior. Server RBAC remains authoritative.
