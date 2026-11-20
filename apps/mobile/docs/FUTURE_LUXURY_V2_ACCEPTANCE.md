# MARINA SMART MOBILE — FUTURE LUXURY V2 · Acceptance notes

This is **real Expo/React Native UI source** in `apps/mobile`, based on PR #340. This branch is a Draft PR into `fix/marina-mobile-session-boundary`, **not** a production merge. Server contracts, 401/503 enforcement and tenant isolation remain owned by the platform.

## Delivered screen work

| Role/area | Verified source of information | UI behavior | No-data behavior |
| --- | --- | --- | --- |
| OWNER | `dashboard()` | Occupancy ring/KPI, confirmed payment KGS, active booking balance, staff/tasks, arrivals/departures, allowed shortcuts | No historical/finance trend fabricated; `—` if optional active counter is absent |
| MANAGER | `dashboard()` | Operational shift briefing before shortcuts, live booking and task indicators | Existing Dashboard API error/retry |
| RECEPTION | `reception()` | Search by guest/room/booking/phone, colored booking/room states, booking details | Search empty/error states |
| PMS | `pmsGrid()` | Horizontal seven-day matrix, today highlight, distinct reservation/HOLD/technical block/collision, details only for permitted role | No rooms/503/auth errors |
| MAID / TECHNICIAN | Existing Staff API | Prioritized visible tasks, urgent filter, responsive room cards, room filters, active repair queue and completed history | No phantom task count before API returns |
| STAFF MANAGER | `listStaff()`, `listTasks()` | Team portraits from initials, assignment/inspection queues and server-ACK-only mutations | Unknown write result locks repeat submission |
| WhatsApp | Inbox/conversation GET and internal note/claim/status ACK | Chat initials, states, inbound/outbound/internal bubbles, delivery labels | **NO outbound WhatsApp input or fake delivery**; shared staging 503 stays blocked |
| MARINA AI | `assistantCapabilities()`, `assistantChat()` | Premium orb, processing state, server ACK only; clear read-only disclaimer | No fabricated reply; shared staging 503 stays blocked |
| COOK / WAITER | Kitchen/Dining APIs | Localized order statuses and role-safe transitions | 503 remains blocked |

The original MARINA SMART raster logo stays unchanged. No unverified brand asset or invented financial number has been added. All newly introduced presentation labels are RU/KG/EN/KZ.

## Automated gates

Required on the **same final SHA**: `npm ci`, `npx expo install --check`, backend contract verification, `npm run typecheck`, `npm run lint`, `npm test -- --ci`, `npm run web:export`, `npx expo config --type public --json`, Android standalone release APK compile/manifest/signature validation.

See GitHub Actions for actual PASS/FAIL and the APK artifact. A successful web export is **not** evidence of a working Android screen.

## Mandatory native visual QA — NOT TESTED until real evidence is attached

Capture **genuine screenshots from the running application**, not design renders:

- Dimensions 320, 375 and 430 dp (Android), font scaling 100/150/200%.
- OWNER and MANAGER overview (with permission-scoped real API fixtures), RECEPTION search + bookings, PMS seven-day scroll and technical block.
- MAID, TECHNICIAN, COOK and WAITER dashboards plus task detail, staff assignment and repair history.
- WhatsApp unavailable/available/read-only states; AI unavailable/processing/response only after server ACK.
- Light and dark theme, keyboard open on login/reception search/internal notes/AI, narrow safe areas.
- No horizontal overflow, no clipped hotel/guest names, 44+ dp touch, TalkBack labels, reduced motion, no flicker, no double write.
- Property A → B switch: old hotel data and messages must never appear after switch. Shared 503 still inaccessible.

Before/after screenshots and optional short Android animation recording: **NOT CAPTURED**. Native LIVE hotel E2E, device FPS and pixel-level logo master comparison: **NOT TESTED**.

## Server dependencies (not fixed in this UI-only PR)

- WhatsApp outbound multi-property API and delivery acknowledgement.
- Confirmed time-series analytics endpoints for truthful charts/trend arrows.
- Shared preview 503 for Inbox, Dining and AI.
- Device-level Android LIVE E2E using an isolated approved HTTPS server.

**Release rule:** Do not mark FUTURE LUXURY visually final or merge this Draft PR until Android preview and all role screenshots pass review on the same release SHA.
