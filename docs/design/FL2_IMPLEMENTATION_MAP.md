# MARINA SMART FUTURE LUXURY 2.0 — phased implementation map

This is the visual-redesign plan following the Stage 1 source baseline in `docs/design/FL2_FUNCTIONAL_BASELINE.md`. It authorizes no runtime change by itself. Existing operations, route identity, Core contracts, RBAC, property isolation, and error semantics are the non-removal boundary.

## Design contract

| Area | Existing | Proposed | Acceptance gate |
|---|---|---|---|
| Brand | Runtime surfaces currently reference existing, non-canonical assets in app-specific locations. | Install only the approved flat teal-ring master after exact binaries are supplied and verified per `docs/design/APPROVED_LOGO_MASTER.md`; derive sizes only from the verified master. | SHA-256 match, RGBA/transparent corners, no glow/shadow/recolor/skew, same provenance across Admin/Staff/Mobile; customer hotel logo remains separate. |
| Themes | Existing surfaces have mixed theme/token implementations. | A shared semantic visual vocabulary mapped per app, retaining platform-specific implementation; full **light/dark** states. | Every interactive/loading/empty/error/denied/offline state reviewed in both themes. |
| Language | Existing Admin/Staff are strongly RU-oriented; Mobile has locale infrastructure. | Preserve current copy truth, complete planned **RU/KG/EN** UI without inventing functionality; locale expansion is separately reviewed behavior. | Layout and truncation QA in RU/KG/EN; status, money, dates, and error meanings remain equivalent. |
| Motion | Existing CSS/React Native motion and refresh behavior vary. | Short functional transitions: 120–180 ms press/focus, 180–240 ms panel/list state, 240–320 ms navigation/detail; opacity/transform only where possible; reduced-motion path. | No motion delays commits, masks polling, changes focus order, or implies success before server acknowledgement. |
| Responsive | Admin/Staff web and Mobile support different viewport constraints. | Preserve information density while clarifying hierarchy; progressive disclosure only when all actions remain reachable. | 320/375/768/1440 px, keyboard, safe-area, font scaling and touch-target QA. |

The approved logo state is **INSTALLED IN THE DESIGN CANDIDATE; PUBLIC DEPLOYMENT NOT CLAIMED**. PR #448 installed the exact approved 1024px RGBA PNG in Admin, Staff and Expo. `node scripts/install-approved-marina-logo.mjs --verify-installed` passed again on 2026-11-14 at candidate `b3bcf042`. The installed master SHA-256 is `24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356`; the approved 512px reference SHA-256 remains `8b41fcf0ca7a6069b90331aa17a7f23e6650ad86d5c01c0f1aab4f5a5c22d739`. Historical installation-pending notes describe the pre-#448 state; they are not the current candidate status.

## Delivery phases by module

| Phase / modules | Existing behavior to retain | Proposed visual work | UX animation plan | Test acceptance gates |
|---|---|---|---|---|
| 0 — evidence lock | 26 Admin tabs, 30 Mobile route modules, Staff routes/modules, Core route/RBAC source | Land inventory/guard only; no UI | None | `design:fl2:audit`, static validators, `git diff --check`; baseline review. |
| 1 — foundations and shells | Admin auth/session/module navigation; Staff gateway/role dispatch; Mobile providers/auth/tab redirects | Tokens, typography, spacing, focus, surfaces, approved logo integration after binary verification | shell transition only; reduced motion; never animate auth truth | Auth/session/401, role/module redirects, property binding, RU/KG/EN and light/dark; no hotel selector added. |
| 2 — PMS and reception | DASHBOARD, PMS, RATES, GROUPS, REQUESTS, RESERVATIONS, CHANNELS; Mobile overview/pms/reception/booking/holds/reservation | Dense operational hierarchy, clear lifecycle/status, conflict and money emphasis | grid selection, drawers and preview→commit state; no speculative success | booking/request distinction, conflict/preview/commit, holds, rates/groups, check-in/out, cash/payment permissions; TTHotel remains explicitly unverified. |
| 3 — operations and staff | OPS, STAFF; My Shift; Mobile tasks/rooms/requests/admin/detail/create | Role-oriented queues, assignment/state clarity, accessible task timelines | list insertion/status transition tied to acknowledged result | claim/assign/status/history, room-state owner/manager gate, unknown outcome, shared identity fail-close, STORE_STAFF placeholder retained. |
| 4 — dining and kitchen | DINING; Staff kitchen/today/waiter; Mobile dining/kitchen/meal plans | Service-date, table, order, production and entitlement hierarchy | status progression and ready cue with reduced-motion equivalent | menu draft/publish, table/session/order state machines, COOK/WAITER separation, entitlement write/readback, folio. |
| 5 — guest/service/growth | SERVICES, SERVICE_SETTINGS, GUESTS, OFFERS, MARKETING, GROWTH, ROOM_QR, POINT_QR | Guest timeline, consent, offers, reviews, token/QR and service-point clarity | timeline reveal and non-blocking feedback only | identity conflicts, consent/history, token/admin boundary, PIN secrecy, review state, payment capability; no connectivity claims. |
| 6 — finance/content/comms/AI | FINANCE, REPORTS, CONTENT, INBOX, WHATSAPP, HOTEL_RULES, SETTINGS; Mobile finance/inbox/conversation/AI/profile | Financial legibility, draft/publish states, assignment/capability panels, settings safety | chart entrance only after data; message/state changes after ack; disable decorative AI “thinking” if unconfigured | KGS/date totals, exports, draft/publish, assignment/send rules, capabilities fail-closed, owner-only WhatsApp/settings actions; AI/WhatsApp LIVE checks separate. |
| 7 — convergence and release evidence | all above plus Guest OS/public routes affected by shared design primitives | Cross-surface consistency polish; no feature expansion | performance budget and reduced-motion audit | full existing CI/contracts, role/property negative matrix, visual matrix, physical Android E2E, explicit release approval; no automatic production/demo rollout. |

## Module-level non-removal checklist

- Admin: every `Tab` remains selectable only through its current module/enabled-module gate and renders its current board. Keep the Legacy/Future Luxury preference during staged rollout until removal is separately approved.
- Staff: preserve `/`, `/kitchen`, `/kitchen/today`, `/waiter`; single-property and shared-preview branches must not be visually conflated.
- Mobile: preserve all route modules and route-local guards. The connected session remains a single property; no hotel-selection proposal is included.
- Core: visual work must not change endpoint paths, methods, payloads, response validation, role/module checks, trusted property resolution, migrations, or data.
- Integrations: TTHotel/PIN, WhatsApp, AI, Telegram, acquiring, realtime, NFC and voice must show capability/configuration/connection truth. A source route or button never justifies “connected.”

## Visual and interaction acceptance matrix

For each redesigned module capture: default, loading, empty, populated, validation error, permission denied, expired session, server error, and destructive/financial confirmation where applicable. Review light/dark × RU/KG/EN at 320, 375, 768, and 1440 px where the platform supports that size. Mobile additionally requires font scaling, safe areas, keyboard, camera denial, offline/timeout, central 401, and mutation acknowledgement/unknown-result paths.

Automated gates must include the baseline guard plus the relevant existing suites. Manual gates must record reviewer, commit, device/browser, locale/theme/role/module/property, result, and evidence path. **LIVE NOT VERIFIED** remains until authorized environment evidence exists. **Android E2E NOT VERIFIED** remains until a physical Android end-to-end run is recorded.
