# MARINA SMART Mobile — live scope and release gate (2026-11-03)

**Isolation:** application-only change set in `apps/mobile`; backend, production, deployed demo, migrations and hotel data are untouched. Source base: mobile `6dc8c0f834cef7d06baf3e42ee24810246cb7148`; backend reference `34d705d2f126a60bd44c2fd17375d97f17dd9025`. These are comparison snapshots, not a unified production release.

## Source-of-truth decisions
- One hotel connection, same platform cookie and module permissions; no separate PMS or payment ledger.
- LIVE screens never render synthetic hotel data. The isolated pre-existing demo workspace remains labelled and unchanged.
- Frontend tab gating is not authorization; server role, module, tenant/property and feature flags remain decisive.
- On unknown outcome of a critical mutation never auto-repeat the request. Use a fresh server read and manual investigation.
- Native platform and WhatsApp provider E2E are separate release gates; passing tests does **not** imply deployed connectivity.

## Platform module coverage

| Platform section | Mobile scope in this change | Status / dependency |
|---|---|---|
| DASHBOARD | Owner/manager overview, real `/admin/dashboard`, drill-in to PMS/Inbox and operations | LIVE read; no false profit/overdue labels |
| PMS | Live physical-room seven-night grid, reservation availability, booking preview/commit | PARTIAL; editing dates/room and full wider chessboard not yet mobile |
| RATES | No live mobile UI | BLOCKED from mobile release scope |
| GROUPS | No live mobile UI | BLOCKED from mobile release scope |
| REQUESTS | Existing `requests` screen represents **maintenance**, not CRM | CRM UI NOT IMPLEMENTED |
| AGENTS | AGENT can view masked PMS and create via authorized preview/commit | PARTIAL; own-agent backoffice not implemented |
| RESERVATIONS | Reception today, reservation detail, guarded check-in/out | PARTIAL; Folio flows and mobile history not yet built |
| SERVICES | Existing operational guest requests | PARTIAL; separate service center missing |
| DINING | Cook queue/valid kitchen status transitions; waiter floor, tables and claim | PARTIAL; waiter fulfillment and many dining operations missing |
| SERVICE_SETTINGS | No live mobile UI | NOT IMPLEMENTED |
| GUESTS | Basic guest context from authorized reservation details | PARTIAL; guest CRM not implemented |
| OFFERS | No live mobile UI | NOT IMPLEMENTED |
| MARKETING | No live mobile UI | NOT IMPLEMENTED |
| GROWTH | No live mobile UI | NOT IMPLEMENTED |
| FINANCE | Dashboard reads confirmed received payments and active reservation balance | READ-ONLY; manual payment/returns not implemented |
| REPORTS | Day metrics in dashboard | PARTIAL; historical charts, export not implemented |
| CONTENT | No CMS authoring | NOT IMPLEMENTED |
| ROOM_QR | Existing connection scanner is **hotel API connection**, not guest QR | Guest QR issue/rotate NOT IMPLEMENTED |
| POINT_QR | No live mobile UI | NOT IMPLEMENTED |
| INBOX | Live conversations, read up to 500 messages/conversation, claim, status, internal notes | PARTIAL; channel sender backend needed |
| WHATSAPP | WhatsApp Inbox for authorized owner/manager/reception; backend filters reception | SENDING BLOCKED; current server send-text is Telegram-only |
| OPS | Existing housekeeping, maintenance, assignment and inspection preserved | PARTIAL; photo upload and task-ID read contract missing |
| STAFF | Existing staff overview and task assignment | PARTIAL; owner staff creation/patch not added |
| SETTINGS | App profile and hotel connection settings | PARTIAL; hotel setup/settings not added |
| HOTEL_RULES | No knowledge editing or AI scenario builder | NOT IMPLEMENTED; assistant read-only endpoint exists separately |
| CHANNELS | No OTA management UI | NOT IMPLEMENTED; platform does not prove full live OTA sync |

## Server dependencies before claiming complete production mobile app
1. **WhatsApp:** GREEN-API outbound sender for MANAGER/RECEPTION with provider id, statuses, deduplication, safe tenant binding, handoff race controls and encrypted secrets server-side. Do not call Telegram-only send-text from mobile.
2. **Auth/runtime:** shared-auth preview currently blocks workspaces. Multi-hotel aggregation and switching must be guaranteed by an accepted server-side tenant/runtime contract, never a client-side property ID.
3. **Reception payment:** server has OWNER/MANAGER hard guard plus `ENABLE_PAYMENT_OPERATIONS` flag. Add an explicit tested permission policy before reception Payment write exists.
4. **Booking retry:** server does not yet prove a queryable idempotent recovery path for a lost `new/commit` response. Mobile blocks automatic retry and displays reconciliation guidance.
5. **Task photo uploads:** secure scoped attachment upload/download and server-side evidence binding are needed. Sending `evidence_urls: []` is not a photo feature.
6. **Notification/realtime:** push token registry with logout/revocation/property isolation; native WebSocket Origin/cookie policy test. HTTP refresh is used until confirmed.
7. **Full modules:** mobile adapters and verified RBAC for remaining sections (RATES/GROUPS/CRM/etc.) must be added before any 26/26 claim.

## CI / verification levels
- Source test (Jest/TypeScript/ESLint/Expo web export) — see `MARINA STAFF Mobile Checks` workflow on PR #290; results depend on the actual selected commit. No local environment installation is claimed.
- Android release APK — only if `android-preview` workflow job succeeds and its signed standalone artifact exists. Do not represent the prior 0.1.0 APK as this new code.
- Runtime E2E (owner, reception, cook, waiter, agent) with authorized hotel identities — **NOT RUN** here.
- Production/shared-auth multi-property isolation, concurrent booking/holds, checkout and financial reconciliation — **NOT RUN** here.
- Real WhatsApp two-way delivery and human/AI handoff — **BLOCKED** by server integration.
- Real Android performance/accessibility, offline and push — **NOT RUN** here.

**Release recommendation:** keep this work on isolated PR until mobile CI passes and server-dependent P0 checks have owners/acceptance evidence. Never silently merge to platform main or deploy it over a hotel.
