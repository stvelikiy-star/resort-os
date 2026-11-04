# MARINA SMART MOBILE · FUTURE LUXURY V3 — visual acceptance matrix

**Scope:** `apps/mobile` only, Draft PR #342 (base: `fix/marina-mobile-session-boundary`). The evidence status below is intentionally conservative. Passing TypeScript/Jest/Expo export/Android APK build **does not** constitute visual acceptance.

## Route-by-route device matrix

For each route, validate **light/dark**, **RU/KG/EN/KZ**, **320 / 375 / 430 dp**, **100 / 150 / 200% font**, successful / loading / empty / error states, roles/permissions, TalkBack accessibility and Reduce Motion.

| Route | Roles / purpose | New V3 UI / regression checks | Real-device screenshots |
| --- | --- | --- | --- |
| `/connect` | Select demo/trusted hotel | Hotel identity, secure entry, QR route, label distinction | NOT CAPTURED |
| `/login` | All server-supported roles | Branded sign-in, keyboard, errors, auth-mode unavailable | NOT CAPTURED |
| `/scan` | Hotel QR connection | Permission and camera-unavailable state | NOT CAPTURED |
| `/overview` | OWNER/MANAGER | Responsive occupancy ring, genuine paid/debt KPI, actual room conditions, role-safe shortcuts | NOT CAPTURED |
| `/reception` | RECEPTION | Search/clear, arrivals/departures/staying filters, badges/guest initials | NOT CAPTURED |
| `/pms` | OWNER/MANAGER/AGENT | Sticky room labels, 7-day horizontal scroll, weekdays, HOLD vs tech block, today, state filter | NOT CAPTURED |
| `/new-booking` | Permitted booking creator | Valid dates, available inventory, confirmed server price, unknown-write lock | NOT CAPTURED |
| `/reservation/[id]` | Permitted booking detail | No unauthorized booking changes | NOT CAPTURED |
| `/holds` | OWNER/MANAGER where server supported | Hold card, correct dark-theme selected state; 503 remains blocked | NOT CAPTURED |
| `/inbox` | Permitted OWNER/MANAGER/RECEPTION | Needs reply, search, server-confirmed timestamp and assignee; no fake unread count | NOT CAPTURED |
| `/conversation/[id]` | Permitted inbox users | Real inbound/outbound/internal bubbles, timestamps and delivery; notes only, no outbound send | NOT CAPTURED |
| `/ai` | Permitted OWNER/MANAGER/RECEPTION | AI Orb, processing placeholder, answer after server ACK, disabled composer offline | NOT CAPTURED |
| `/tasks` | MAID/TECHNICIAN and other permitted staff | Sorted priorities, visible/urgent filters, honest completion count | NOT CAPTURED |
| `/task/[id]` | Permitted task detail | Badge semantics, checklist progress, photo feature unavailable, server ACK-only write | NOT CAPTURED |
| `/rooms` | Permitted staff | 1/2 column responsive cards, clean/attention filtering, partial-data notice | NOT CAPTURED |
| `/room/[id]` | Permitted staff | Premium state card, contrast, task list, no invented occupancy | NOT CAPTURED |
| `/requests` | TECHNICIAN and permitted maintenance staff | Active/urgent queue + completed history | NOT CAPTURED |
| `/new-request` | Maintenance creator | Premium form, category icons, room-loading state and unknown-POST lock | NOT CAPTURED |
| `/admin` | OWNER/MANAGER if authorized | Team initials, inspection/assignment queues, write-lock behavior | NOT CAPTURED |
| `/dining` | COOK/WAITER/authorized management | Actual menu items where present, kitchen statuses, unknown-safe table status | NOT CAPTURED |
| `/profile` | All authenticated staff | Role identity, translated labels, four language choices at large font, theme switching | NOT CAPTURED |
| `/more` | Roles with >4 allowed navigation tabs | Hidden tab buttons remain routable, unauthorized routes still denied | NOT CAPTURED |

Also test the redirect root `/` and modal navigation/back behavior.

## Required original evidence

For each priority screen capture a **real running app screenshot** (both themes) at 320/375/430 dp. Compare before/after by same hotel, role, fixture, locale and device dimensions. Include keyboard, enlarged font, loading/error and reduced-motion recordings. Save native images in review artifacts; **do not substitute design renders**.

**Current visual acceptance:** NOT RUN — this environment has no Android emulator/ADB configured and no authenticated on-device screenshot pipeline. Android APK compilation checks binary correctness, not pixel appearance or interaction on a device.

## Separately tracked backend dependencies (not part of this PR)

- WhatsApp outbound messaging not permitted by confirmed server API; no send input.
- Shared-auth preview may return 503 for Inbox, Dining and MARINA AI; no bypass.
- AI read-only, no voice/audio promise.
- Historical revenue/occupancy time-series unsupported; no fabricated trend chart.
- Live multi-hotel Android E2E must be validated against an approved isolated environment after UX QA.

**Merge policy:** Draft PR stays unmerged until visual evidence is supplied and reviewed. The exact source SHA, CI result, and APK run must match the candidate being accepted.
