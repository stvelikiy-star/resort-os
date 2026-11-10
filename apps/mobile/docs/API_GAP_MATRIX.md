# Confirmed mobile API surface & blockers (read-only contract audit)

Backend comparison snapshot: `34d705d2f126a60bd44c2fd17375d97f17dd9025` from `stvelikiy-star/resort-os`. Mobile transport uses HTTPS, native cookie credentials and server tenant binding. Below are routes **verified in backend source**; availability in a particular deployed hotel has not been proven.

| Screen / role | Method / endpoint | Behaviour | Error contract | Status |
|---|---|---|---|---|
| Owner/manager dashboard | GET `/api/v1/admin/dashboard` | live occupancy, receipts, tasks | 401/403/503 | PARTIAL live E2E |
| Reception | GET `/api/v1/admin/reception/reservations` | today's authorized bookings | 401/403/503 | PARTIAL |
| Reception detail | GET `/api/v1/admin/reception/reservations/{id}` | guest, schedule, payments and room status | 401/403/404 | PARTIAL |
| Reception check-in/out | POST `/api/v1/admin/stays/reservations/{id}/check-in` and `check-out` | trusted session and room checks | 401/403/409 | PARTIAL live E2E |
| PMS | GET `/api/v1/pms/grid?start=&end=` | one physical room per row, [start,end) | 401/403/422 | READ |
| Booking preview/commit | POST `/api/v1/admin/pms/reservations/new/preview` and `new/commit` | server-priced two-step write; no client booking ledger | 401/403/409/422 | PARTIAL recovery after timeout |
| HOLD | GET/POST/DELETE `/api/v1/admin/pms/holds` | 60min server-controlled inventory hold | 401/403/409/422 | PARTIAL |
| Inbox | GET `/api/v1/admin/inbox/conversations`, GET `/{id}` | server-filtered conversations and history | 401/403/404 | READ |
| Inbox status/claim/note | PATCH `/{id}/status`, POST `/{id}/claim`, POST `/{id}/notes` | staff authorization; internal note, not guest message | 401/403/409 | PARTIAL |
| Kitchen | GET `/api/v1/kitchen/orders`, PATCH `/{id}/status` | cook queue and transitions | 401/403/409 | PARTIAL |
| Waiter | GET `/api/v1/dining/floor`, PATCH `/dining/orders/{id}/waiter` | live table and waiter assignment | 401/403/409 | PARTIAL |
| Assistant | GET `/api/v1/assistant/capabilities`, POST `/api/v1/assistant/chat` | OWNER/MANAGER/RECEPTION, read-only, rate-limited | 401/403/422/429 | UI implemented; live E2E BLOCKED |

**Change requests to backend (not performed here):** WhatsApp outbound with GREEN-API provider receipts/dedup; guest session contract; cookie-to-native token/device refresh/revocation where required; idempotent booking-write query after lost acknowledgement; photo/attachments; push registry; live multi-property scope and aggregate owner API; accurate property-local current date for agent/reception if needed.

**Security:** the mobile code does not expose GREEN-API secrets, use 3rd-party direct-send endpoints, write to local PMS replicas or claim a 200 response without server confirmation.
