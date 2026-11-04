# MARINA SMART — server/mobile contract handoff (2026-11-04)

**Purpose:** coordination only; server is canonical business logic. No changes to `apps/mobile`.
Baseline SERVER SHA: `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` (shared operations #317); MOBILE SHA: `50848a05837b86ea2313a74cbf35e019fc5e66fb` (mobile #315).
**Important correction:** both task routes were already implemented at server SHA
`7ad9aace2da7da87d4f022a81d3a41d9b99d3605`, in
`operations_assignment.py` and `staff_task_reports.py`, but were **blocked (503)**
by the isolated shared-auth allowlist. PR #318 scopes/open these existing
routes, closes custom OPS role escalation in assignment, rejects omitted
assignment intent, and validates a five-code cleaning report in shared staging.
The first duplicate implementation was removed after the Release Gate caught
it. No duplicated routes remain by source inspection; exact final CI required.
CI is **not an external LIVE environment**.

PR filenames checked: platform PRs #314/#316/#317 modify **zero files also changed** by
mobile PRs #311/#313/#315. The mobile stack additionally modifies the mobile CI file
`.github/workflows/marina-staff-mobile-check.yml` (outside `apps/mobile`), which
the platform stack did not touch. Do not auto-merge either stack to `main`.

## Verified route contract matrix

**Column notation:** SERVER SHA / MOBILE SHA appear in every row, in full. STATUS is
limited to source/CI knowledge (no deployed LIVE claim).

| ENDPOINT | SERVER SHA | MOBILE SHA | STATUS | BLOCKER |
|---|---|---|---|---|
| `POST /api/v1/auth/login` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **INCOMPATIBLE with shared preview** | Server requires tenant_code + property_code; mobile sends username/password only. Legacy pinned-property login is separate. Native cookie persistence/device tokens not externally accepted. |
| `GET /api/v1/auth/me` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SOURCE COMPATIBLE | Identity/permissions validated locally; native session continuity and hotel context in one shared runtime untested. |
| `GET /api/v1/pms/grid` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SOURCE COMPATIBLE | Shared two-hotel browser tested, but mobile real device not tested. Mobile room list still derives from tasks instead of grid. |
| `GET /api/v1/admin/reception/reservations`; `GET /{uuid}` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SOURCE COMPATIBLE | Property-scoped route; no external mobile E2E. |
| `POST /api/v1/admin/pms/reservations/new/preview`, `/commit` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SERVER CI PASS | Mobile request/ack needs final shared-auth login and device E2E; no charge is initiated. |
| `GET/POST /api/v1/admin/pms/holds`; `DELETE /{uuid}` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **INCOMPATIBLE (mobile gate)** | `CONFIRMED_BACKEND_FEATURES.pmsHolds=false`; also server `holds` array uses snake_case (`room_id`, `expires_at`), mobile `Hold` type expects camelCase. Fix mobile only after pinned shared source contract accepted. |
| `POST /api/v1/admin/stays/reservations/{uuid}/check-in`, `/check-out` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SERVER CI PASS | Mobile security semantics of one-time PIN and real device role sessions untested. |
| `GET /api/v1/ops/tasks`; `POST /tasks`; `POST /tasks/{uuid}/claim`; `PATCH /tasks/{uuid}/status` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SERVER CI PASS (MAID/TECH) | Owner/manager and two hotel task lifecycle proven in disposable CI, not external device LIVE. Role/OPS grant remains authoritative. |
| `PATCH /api/v1/ops/tasks/{uuid}/assignee` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **EXISTS, SHARED 503 AT BASELINE** | Canonical `operations_assignment.py` accepts existing OPEN/IN_PROGRESS assignment with hotel-local role check; draft #318 adds strict OWNER/MANAGER + OPS ceiling, explicit nullable field, shared allowlist and E2E. No LIVE proof. |
| `POST /api/v1/ops/tasks/{uuid}/complete-report` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **EXISTS, SHARED 503 AT BASELINE** | Canonical `staff_task_reports.py` returns `task_id` (mobile already accepts it), requires assigned MAID and IN_PROGRESS, transitions to IN_INSPECTION; draft #318 enforces five-code checklist and denies unverified URLs in shared mode. |
| `PATCH /api/v1/ops/rooms/{uuid}/state` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **BLOCKED in shared preview** | Legacy route owner/manager only; shared runtime 503. Mobile must not offer to MAID/TECH or bypass inspection. |
| `GET /api/v1/admin/staff/overview` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SOURCE COMPATIBLE | Granted role/section only; no full mobile role provisioning E2E. |
| `GET /api/v1/admin/booking/reservations/{uuid}/acquiring-readiness`; `POST /payments` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | SERVER INTERNAL LEDGER ONLY | Staff-recorded money only, not bank/acquiring. Mobile does not implement this write path. |
| `GET/PATCH/POST /api/v1/admin/inbox/conversations[/{uuid}/...]` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **BLOCKED in shared preview** | Backend exists in legacy mode; shared boundary 503. Real hotel-specific GREEN-API delivery/handoff not accepted. |
| `GET /api/v1/assistant/capabilities`; `POST /assistant/chat` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **BLOCKED in shared preview** | No verified shared hotel AI, role-specific hotel knowledge or real LLM/human handoff. |
| `GET /api/v1/kitchen/orders`; `GET /api/v1/dining/floor` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **BLOCKED in shared preview** | COOK/WAITER operational cabinets not accepted. |
| `/api/v1/guest-os/*` and guest QR | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **BLOCKED in shared preview** | Guest QR, guest sessions, property-specific services and KÖL link require their own E2E. |
| `GET /api/v1/ops/day-summary` | `7ad9aace2da7da87d4f022a81d3a41d9b99d3605` | `50848a05837b86ea2313a74cbf35e019fc5e66fb` | **NOT IMPLEMENTED** | Mobile deliberately throws NOT_FOUND; define scoped summary contract in later approved P0/P1 stage. |

## Mandatory Claude Code mobile follow-ups (do not edit from platform branch)

1. Preserve auth `tenant_code/property_code` at shared-login or obtain an agreed mobile-specific
   tenant selector flow. Verify revocation and native cookie/session persistence; no mobile
   fixed-hotel host may silently select another owner's property.
2. Once a **specific final server SHA** is accepted, enable HOLD and normalize server
   snake_case HOLD records into the mobile model. Keep permission and quote behavior server-side.
3. Consume the reviewed `assignee` and `complete-report` acknowledgments; report
   means `IN_INSPECTION`, not `DONE` or `CLEAN`. Never auto-retry a write after unknown outcome.
4. Hide or disable blocked shared routes (rooms state override, inbox, AI, kitchen, dining,
   guest QR); do not interpret a route in source as deployed availability. Match permissions
   and test on **real device + isolated shared staging** when the backend is accepted.
5. Mobile #315 source requires separate security/CI acceptance; it is not LIVE proven.
   Do not merge Claude Code branches into RC2 without permission.

## Platform next work

Finish P0 hardening and shared staging exposure of the **existing**
assignment/report routes. Independently verify 2-hotel real-browser/PostgreSQL
E2E, role ceilings, explicit assignment, checklist report audit and rollback.
Retain reviewed RC2 #314 and its 64/64 gates immutable. No DEMO, APK, Ubuntu or
production data modification in this handoff.
