# MARINA SMART Mobile · Read-only baseline audit (03.11.2026)

Source compared: mobile PR #290 head `7ecff8e65672eddb9425c0d92fa7d133163ab93a`, design PR #289 head `5e9eb6cbc1db4b65701ace09cd45da4d475cb402`. This is a **design-only continuation** of PR #290; previous design PR #289 was not force-merged or overwritten.

| Surface | Starting state | Evidence / action |
|---|---|---|
| Multi-hotel connection, native secure URL validation | EXISTS | `src/api/hotels.ts`, `src/state/session.tsx` |
| Login, logout and revoked session recheck | PARTIAL | `src/state/session.tsx`; device-scoped tokens not provided by platform |
| OWNER/MANAGER LIVE dashboard | EXISTS | `app/(app)/overview.tsx`, `/api/v1/admin/dashboard` |
| Mobile PMS, booking preview/commit, HOLD | PARTIAL | `app/(app)/pms.tsx`, `new-booking.tsx`, `holds.tsx`; platform executes writes |
| RECEPTION LIVE reservation, check-in/out | PARTIAL | `app/(app)/reception.tsx`, `reservation/[id].tsx`; payment release flag must be verified |
| WhatsApp read-only conversation, claim/notes/status | PARTIAL | `app/(app)/inbox.tsx`, `conversation/[id].tsx` |
| WhatsApp outbound send and AI hand-off | BLOCKED | no confirmed compatible server send-text for WhatsApp |
| MAID/TECHNICIAN tasks/inspection/maintenance | EXISTS/PARTIAL | `app/(app)/tasks.tsx`, `task/[id].tsx`; photo evidence API missing |
| COOK/WAITER orders and floor | PARTIAL | `app/(app)/dining.tsx`; server role endpoints distinct |
| AGENT scoped grid | PARTIAL | `app/(app)/pms.tsx`; agent holds intentionally forbidden server-side |
| STORE_STAFF, CONTENT_MANAGER, BEACH_PARTNER | MISSING | no confirmed mobile-safe server contract |
| GUEST | BLOCKED | separate guest session/role and property/stay isolation not signed off |
| Light/Dark themes | PARTIAL | previous `ThemeProvider.tsx` selected mode but had no persisted preference |
| Future Luxury motion | PARTIAL | prior per-component opacity/spring animations; no centralized tokens or measured device FPS |
| Logo | PARTIAL | existing `assets/marina-staff-app-icon.png` is used; vector source sign-off not available |
| Native Android/iOS runtime & performance | BLOCKED | cannot infer from static code or web export |

**Safety boundary:** all changes are confined to `apps/mobile`; no server, migration, infrastructure, deployed demonstration or hotel data mutation is part of this design PR.
