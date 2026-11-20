# MARINA SMART MOBILE — RC8 operational acceptance (2026-11-06)

**Code:** mobile stacked PR #391 → #392; reference platform PR #385 (`e4ca82517dea03f1768419d61e876b81df4b8b21`). This is evidence of **source contracts**, NOT a production acceptance certificate.

## P0 route gates

| Workstream | Source route | Mobile behavior | Acceptance |
|---|---|---|---|
| WhatsApp capabilities | GET `/api/v1/admin/inbox/outbound-capabilities` | Requires server `whatsapp.configured=true`, `human_only`, `queued_only`; strict role+grant; 403/503 fail closed | Code integrated; REAL provider UAT BLOCKED |
| Human WhatsApp text | POST `/api/v1/admin/inbox/conversations/{id}/send-text` | `Idempotency-Key`, durable unresolved journal, no POST retry; server `QUEUED` not delivery; RECEPTION requires claimed chat | Code integrated; SENT/DELIVERED callbacks unconfirmed |
| New booking | POST `/api/v1/admin/pms/reservations/new/preview` → `/commit` | Existing preview/commit, RECEPTION CORE_RATE only, 403 authoritative | Code present; real PMS readback NOT RUN |
| Modify booking dates | POST `/api/v1/admin/pms/reservations/{id}/schedule/preview` → `/commit` | OWNER/MANAGER + PMS/RESERVATIONS, single segment only, optimistic `expected_version`, confirmation required | Code integrated; server readback NOT RUN |
| Cancel booking | No verified canonical cancel route on pinned platform | No cancel button; do not fabricate action | **BLOCKED** |
| HOLD | Mobile pinned verifier blocks HOLD | No unsupported HOLD writes | **BLOCKED** |

## Role acceptance matrix

| Role | Visible protected operations | Evidence still required |
|---|---|---|
| OWNER | Dashboard, PMS, finance, inbox/WhatsApp, tasks, team, AI (within grants) | Live HTTPS auth, per-operation persistence, revocation |
| MANAGER | PMS, finance, inbox/WhatsApp, tasks, team, AI (within grants) | Live API scope, server 403 on other scopes |
| RECEPTION | Arrivals, reservations, check-in/out, booking core rate, claimed WhatsApp only | Server 403 for unclaimed chat, 409 conflict |
| MAID | Housekeeping task list/change states, room-related reads | Read-after-write, no other room's hidden data |
| TECHNICIAN | Maintenance tasks and repair request, authorized room reads | Task state transitions persisted |
| COOK | Kitchen order list and authorized state updates | Real kitchen server and status readback |
| WAITER | Dining-floor reads and waiter-claim action | Real waiter server scope and order assignment |
| STORE_STAFF | Profile only | **BLOCKED** until storage inventory API established |

## Non-negotiable Android E2E before commercial release

- Install *new final-head APK* with verified signature, package ID, bundled JS and exact SHA.
- Use physical Android + verified single-hotel HTTPS endpoint; confirm signed trust origin and cookie session; no arbitrary hotel picker for normal staff.
- Run role-based read → mutation → server readback; verify same-hotel alignment between app and platform, no cross-property leakage.
- Test logout/offline/401 revocation, blocked 403, unavailable 503, duplicate tap, lost write ACK and app relaunch.
- Test RU/KG/EN, light/dark, navigation, reduced-motion and screen widths 320/360/393dp (Expo Web images do not equal Android evidence).
- Provider WhatsApp QUEUED → SENT/DELIVERED must be verified from real provider webhook, not a client placeholder.

**Status:** Draft. No release approval. Never merge into main or claim production readiness from passing unit tests alone.
