# MARINA SMART FUTURE LUXURY 2.0 — Stage 1 functional baseline

**Audit point:** source tree at `4b355e18`, worktree `fl2-functional-baseline-20261111`, stacked after draft PR 436. **Method:** static source inspection only. **LIVE NOT VERIFIED. Android E2E NOT VERIFIED.** This document is a non-removal contract, not proof that an integration is configured, reachable, or production-ready.

## Scope and evidence rules

- Covered surfaces: Admin PMS, Staff web, Mobile Expo, Core API/RBAC, and relevant source-level tests.
- Baseline counts: **26 Admin tabs**, **30 Mobile route modules** (including layouts, `+html`, and index), four Staff page routes, and the server paths those clients reference.
- “Known” means a source declaration or call site exists. It does not mean runtime connectivity. Absence of evidence is recorded rather than inferred.
- The current Mobile session is property-bound (`property_code`/trusted hotel context). There is **no mobile hotel-selection route in this baseline**; do not add or imply multi-property switching as part of a visual rewrite.
- TTHotel connectivity, WhatsApp provider connectivity, MARINA AI provider/configuration, Telegram, payment/acquiring, and voice/webhook delivery are **uncertain until runtime-verified**. Route/capability source is not connectivity proof.
- Every redesign must retain route identity, role/module gates, property scoping, loading/empty/error states, mutations, confirmations, focus/poll refresh behavior, and keyboard/accessibility behavior.

## Admin PMS inventory — all 26 `AdminShell` tabs

Primary UI/router evidence for every row: `apps/admin/components/AdminShell.tsx`. Server module mapping evidence: `services/api/app/section_permissions.py`; auth/session/property evidence: `services/api/app/auth.py`.

| Module / tab | UI entry and component evidence | Known roles / gates | API evidence paths | Primary operations | Preservation check / confidence / missing evidence |
|---|---|---|---|---|---|
| DASHBOARD | “Главная”; `DashboardBoard.tsx` | `module_permissions` includes DASHBOARD; default OWNER/MANAGER | `manager_dashboard.py`, `owner_intelligence.py`, `owner_operations_analytics.py` | operational/owner summaries and navigation | Keep summary states and deep links. High static confidence; LIVE NOT VERIFIED. |
| PMS | “Шахматка”; `PMSGridV9.tsx` | PMS grant; RECEPTION receives read-only UI; AGENT mode | `pms_chessboard*.py`, `pms_reservation_create.py`, `pms_holds.py`, `room_detail.py`, `room_wayfinding.py` | grid, room/reservation detail, holds, preview/commit booking, schedule | Preserve grid semantics, dates, conflict/preview/commit and read-only modes. High; provider connectivity not evidenced. |
| RATES | “Цены / Сезоны”; `RateManagementBoard.tsx` | RATES; default OWNER/MANAGER | `rate_management.py` | read/create/update rate periods | Preserve period validation and monetary display. High static. |
| GROUPS | overflow; `GroupBookingBoard.tsx` | GROUPS plus hotel module enabled; defaults OWNER/MANAGER/RECEPTION | `group_bookings.py` | availability, create/list group bookings | Preserve enablement gate and availability-before-create. High static. |
| REQUESTS | “Заявки”; `RequestsBoard.tsx` | REQUESTS; server paths distinguish booking requests | `booking_admin.py` | list, quote, confirm payment/request workflow | Preserve request-versus-reservation truth and statuses. High static; acquiring LIVE NOT VERIFIED. |
| AGENTS | overflow; `AgentsBoard.tsx` | AGENTS plus module enabled | `agent_context.py`, `owner_corrections.py` | list/manage agents, interactions, access, reports | Preserve role-sensitive actions and report context. High static. |
| RESERVATIONS | “Ресепшен”; `ReceptionWorkspace.tsx` | RESERVATIONS; default OWNER/MANAGER/RECEPTION | `reception_reservations.py`, `reception_readiness.py`, `reservation_detail.py`, `reservation_payments.py`, `stays.py`, `folio.py` | reservation detail, readiness, payments, check-in/out, folio | Preserve cash/payment gates, lifecycle confirmations and navigation. High static; payment provider LIVE NOT VERIFIED. |
| SERVICES | “Сервис гостя”; `GuestServicesCenter.tsx` | SERVICES; default OWNER/MANAGER/RECEPTION | `guest_services.py`, `staff_guest_requests.py` | list/create guest service work and staff handling | Preserve guest/property context and task lifecycle. High static. |
| DINING | overflow; `DiningManagementBoard.tsx` | DINING plus module enabled | `dining_*.py`, `kitchen*.py` | menu/day, tables, sessions, orders, entitlements, production, folio | Preserve status machines and kitchen/waiter separation. High static; realtime LIVE NOT VERIFIED. |
| SERVICE_SETTINGS | overflow; `GuestServiceSettingsBoard.tsx` | SERVICE_SETTINGS | `guest_service_settings.py` | read/update guest-service policy/settings | Preserve settings round-trip and validation. High static. |
| GUESTS | overflow; `GuestHistoryBoard.tsx` | GUESTS | `guest_crm.py`, `owner_intelligence.py`, `guest_identity.py` | history/profile, preferences, duplicate review | Never silently merge identity; preserve duplicate/conflict states. High static. |
| OFFERS | overflow; `GuestOffersBoard.tsx` | OFFERS plus module enabled | `guest_offers.py` | admin offer management and guest offer delivery | Preserve admin/public boundary and token context. Medium; delivery LIVE NOT VERIFIED. |
| MARKETING | overflow; `MarketingBoard.tsx` | MARKETING plus module enabled | `marketing.py`, `marketing_automation.py` | consent, touchpoints, audience, summaries | Preserve consent evidence and history. High static; outbound automation uncertain. |
| GROWTH | overflow; `GrowthControlBoard.tsx` | GROWTH plus module enabled | `growth_control.py`, `guest_stay_reviews.py` | engagement lifecycle, feedback/stars, candidates, reviews | Preserve opt-in/status and review-link boundaries. High static. |
| FINANCE | “Финансы”; `HotelFinanceBoard.tsx` | FINANCE; API OWNER/MANAGER | `hotel_finance.py`, `reservation_payments.py`, `folio.py` | summary, payment requirement, payments/charges/review | Preserve KGS precision, date scope and authorization. High static; settlement LIVE NOT VERIFIED. |
| REPORTS | overflow; `ReportsBoard.tsx` | REPORTS | `analytics_reports.py`, `owner_intelligence.py` | analytics overview/export | Preserve filters, totals and export. High static. |
| CONTENT | overflow; `SiteContentBoard.tsx` | CONTENT plus module enabled | `site_content.py`, `site_media.py`, `customer_site_page.py` | locale draft/publish and media slots | Preserve draft/publish distinction and locale identity. High static. |
| ROOM_QR | overflow; `RoomQrBoard.tsx` | ROOM_QR plus module enabled | `guest_os.py`, `guest_pin_admin.py`, `room_wayfinding.py` | room access/QR, PIN issuance, directions | Preserve token/PIN secrecy and expiry/error states. Medium; **TTHotel/PIN external connectivity not evidenced**. |
| POINT_QR | overflow; `ServicePointsBoard.tsx` | POINT_QR plus module enabled | `service_points.py`, `service_point_payments.py`, `mkassa_payment_bridge.py` | service points, QR/payment intents | Preserve admin/public/integration boundaries. Medium; mKassa LIVE NOT VERIFIED. |
| INBOX | overflow; `InboxBoard.tsx` | INBOX plus module enabled; API also accepts WHATSAPP on mapped paths | `inbox.py`, `ai_sales.py` | conversations, claim/assign/status, notes, request link, AI draft | Preserve assignment rules and message/request linkage. High static; transport/AI connectivity uncertain. |
| WHATSAPP | top-level; `WhatsAppWorkspace.tsx` | WHATSAPP | `whatsapp_connection.py`, `channel_outbound.py`, `green_api_webhook.py` | connection status/QR, outbound text, workspace | Capability/connection UI must stay fail-closed. Medium; **WhatsApp connectivity LIVE NOT VERIFIED**. |
| OPS | “Уборка / Ремонт”; `OperationsBoard.tsx` | OPS; role/task gates | `operations.py`, `operations_assignment.py`, `operations_history.py`, `housekeeping_schedule.py`, `staff_task_reports.py` | task list/create/claim/assign/status/history, room state | Preserve role/task-type rules and audit history. High static. |
| STAFF | overflow; `StaffBoard.tsx` | STAFF; API OWNER/MANAGER, owner-only mutations where declared | `staff_control.py` | overview, create/update staff | Preserve owner-only gates and active-state controls. High static. |
| SETTINGS | overflow; `HotelSetupBoard.tsx` | SETTINGS | `hotel_setup.py` | property/modules/room types/rooms setup | Preserve destructive confirmations and enabled-module effects. High static. |
| HOTEL_RULES | overflow; `HotelRulesBoard.tsx` | HOTEL_RULES | `hotel_rules.py` | read/update hotel knowledge | Preserve source truth and explicit save state. High static; AI consumption LIVE NOT VERIFIED. |
| CHANNELS | overflow; `ChannelManagerBoard.tsx` | CHANNELS | `channel_reservations.py`, `channel_mappings.py` | mapping, staged import/CSV and confirmed reservation import | Preserve staging, validation, identity conflict and canonical PMS truth. High static; **TTHotel/OTA connectivity not evidenced**. |

Admin shell-wide safeguards: retain `/core/api/v1/auth/mode`, login/me/logout, 30-second session validation, 401 invalidation for Core calls, housekeeping schedule ensure, module-enable fetch, property/hotel identity, Legacy/Future Luxury preference, and the always-present `MarinaAiAssistant`. AI UI presence is not proof of configured AI.

## Staff web inventory

| Module | UI entry | Known roles / gates | API evidence paths | Primary operations | Preservation check / confidence / missing evidence |
|---|---|---|---|---|---|
| My Shift gateway | `/`; `app/page.tsx` → `StaffRoleGateway.tsx` | single-property operational roles; shared preview only verified MAID/TECHNICIAN or COOK/WAITER with DINING and property/tenant identity | `auth.py`, `telegram_auth.py`, `housekeeping_schedule.py` | password/session bootstrap, optional Telegram login/link, role dispatch | Preserve fail-closed shared identity comparisons and single-property behavior. High static; Telegram LIVE NOT VERIFIED. |
| Legacy shift | `StaffShiftV2.tsx`, `GuestRequestShiftPanel.tsx` | OWNER/MANAGER/MAID/TECHNICIAN; request panel also RECEPTION/WAITER | `operations.py`, `staff_guest_requests.py`, `staff_task_reports.py` | shift tasks, claims/status/completion, guest-request queue | Preserve task ownership/status and role-specific panels. High static. |
| Shared dining shift | `SharedDiningShift.tsx` | shared COOK/WAITER, DINING grant, matching tenant/property/session | `kitchen.py`, `dining_control.py` | active kitchen orders or waiter floor/orders | Preserve repeated identity verification and forced session end. High static. |
| Kitchen | `/kitchen`; `KitchenEntry.tsx` | OWNER/MANAGER/COOK | `kitchen.py`, `kitchen_menu_management.py`, `kitchen_arrivals.py` | pulse, Chef Production, orders/statuses; manager menu admin | Preserve NEW→ACCEPTED→COOKING→READY and COOK versus management controls. High static. |
| Kitchen today | `/kitchen/today`; `DiningDayPlanner.tsx` | component/API gates apply | `dining_control.py`, `dining_entitlements.py`, `dining_production_snapshots.py` | day plan, portions/production | Preserve service date and snapshot/commit distinction. High static. |
| Waiter / floor | `/waiter`; `WaiterWorkspace.tsx`, `DiningFloorPlan.tsx` | OWNER/MANAGER/WAITER | `dining_control.py`, `dining_seating.py`, `dining_folio.py`, `kitchen.py` | tables/reservations, seating, order claim/create/serve, folio | Preserve assignment, table/order status and approved-menu constraint. High static. |
| Store placeholder | gateway empty state | STORE_STAFF | no accepted server contour identified | no operational writes | Must remain explicitly unavailable; do not invent stock/sales. High confidence of missing capability. |

## Mobile Expo inventory — all 30 route modules

Gating source: `apps/mobile/src/roles/registry.ts`, `bookingAccess.ts`, `financeAccess.ts`, session state, and route-local checks. “Route module” includes structural Expo files; it does not assert 30 independently navigable screens.

| Route module | UI entry / known gate | API evidence / primary operations | Preservation check / confidence / missing evidence |
|---|---|---|---|
| `(app)/_layout.tsx` | authenticated tab shell; workspace/module gate | navigation only | Keep redirect and compact overflow plan. High. |
| `(app)/overview.tsx` | LIVE OWNER/MANAGER with DASHBOARD | dashboard summaries | Keep property/session refresh and denied states. High static. |
| `(app)/reception.tsx` | RECEPTION workspace + RESERVATIONS | reservation/reception reads and lifecycle entry | Keep role/module gate. High static. |
| `(app)/pms.tsx` | PMS workspace | grid, reservation and booking links | Keep date/selection semantics. High static. |
| `(app)/inbox.tsx` | WHATSAPP or eligible INBOX; shared preview suppressed | inbox conversations | Keep assignment/send gates. Connectivity uncertain. |
| `(app)/dining.tsx` | DINING, COOK/WAITER candidates; shared preview suppressed | dining floor/production | Keep role-specific surface. High static. |
| `(app)/kitchen.tsx` | DINING, OWNER/COOK candidates; shared preview suppressed | kitchen summary/orders | Keep status transitions. High static. |
| `(app)/tasks.tsx` | OPS workspace | operations tasks | Keep task-type filter and claim/status. High static. |
| `(app)/rooms.tsx` | OPS workspace | rooms/state | Keep manager-only state mutation. High static. |
| `(app)/requests.tsx` | OPS workspace | maintenance/guest requests | Keep create permission and task type. High static. |
| `(app)/admin.tsx` | OWNER/MANAGER with OPS+STAFF | staff/task management | Keep dual-module gate. High static. |
| `(app)/profile.tsx` | all authenticated sessions | role/workspaces, sign-out, finance link | Keep unavailable-role truth and logout. High. |
| `(app)/more.tsx` | only when tab overflow exists | navigation only | Keep redirect when unnecessary. High. |
| `(auth)/_layout.tsx` | auth route group | navigation only | Preserve unauthenticated containment. High. |
| `(auth)/connect.tsx` | unauthenticated property/server connection | capability/trust setup | **One property-bound mobile flow; no hotel selector.** Keep trust validation. High static. |
| `(auth)/login.tsx` | connected, unauthenticated | auth login/mode | Keep concurrency and error distinctions. High static; LIVE NOT VERIFIED. |
| `_layout.tsx` | root providers/stack | navigation and session | Keep modal/card presentation and session boundary. High. |
| `+html.tsx` | Expo web HTML wrapper | none | Keep web reset/document behavior. High. |
| `index.tsx` | session-derived redirect | none | Keep role/module home selection. High. |
| `task/[id].tsx` | tasks tab required | task detail/status/report | Keep missing/denied/error states. High static. |
| `room/[id].tsx` | rooms tab required | room detail/state/request links | Keep state mutation gate. High static. |
| `new-request.tsx` | `canCreateMaintenance` | create maintenance | Keep ack/unknown-outcome handling. High static. |
| `scan.tsx` | connect flow/camera permission | parses hotel address QR | Keep permission and trust checks; not hotel selection. High. |
| `ai.tsx` | OWNER/MANAGER/RECEPTION; not shared preview; capability configured | assistant capabilities/chat | Keep disabled-unconfigured state. **AI connectivity LIVE NOT VERIFIED.** |
| `finance.tsx` | LIVE and `canReadFinance` (OWNER/MANAGER + FINANCE) | finance summary | Keep KGS/date/property scope. High static. |
| `holds.tsx` | OWNER/MANAGER + PMS | holds and grid | Keep confirmed-feature guard. High static. |
| `meal-plans.tsx` | LIVE OWNER/MANAGER/RECEPTION + PMS/RESERVATIONS; not shared preview | stays, entitlements, meal-plan write/readback | Keep verified readback and date/portion semantics. High static. |
| `new-booking.tsx` | PMS plus OWNER/MANAGER/AGENT/RECEPTION access helper | grid, preview/commit, agent services | Keep preview-before-commit, retry journal, unknown outcome and role limits. High static. |
| `reservation/[id].tsx` | PMS/reception context | reservation detail/lifecycle | Keep access, status, payment truth. High static. |
| `conversation/[id].tsx` | inbox tab; sending additionally role/assignment/capability gated | conversation detail/send | Keep reception assignment restriction. WhatsApp LIVE NOT VERIFIED. |

## Core API and RBAC preservation matrix

| Domain | Authoritative source evidence | Static contract to preserve | Missing runtime evidence |
|---|---|---|---|
| Authentication/property | `auth.py`, `section_permissions.py`, `app_entry.py` | cookie/session identity, `trusted_property_id`, exact module permissions, custom grant behavior, role ceiling, route inclusion | LIVE sessions and deployment mode not verified. |
| Booking/PMS/stay | `booking_admin.py`, `pms_*.py`, `reception_*.py`, `reservation_*.py`, `stays.py`, `folio.py` | request ≠ reservation; preview/commit; conflicts; payments; check-in/out; property scope | TTHotel/acquirer connectivity not verified. |
| Kitchen/dining | `kitchen*.py`, `dining_*.py` | separate read/write roles, menu draft/publish, order/table/session status machines, entitlements/production/folio | realtime and external delivery not verified. |
| Guest OS/CRM | `guest_*.py`, `service_points*.py`, `room_wayfinding.py` | token-scoped public routes versus admin routes, identity conflict handling, PIN secrecy, requests/offers/reviews | PIN/TTHotel and payment integrations not verified. |
| Finance/reporting | `hotel_finance.py`, `reservation_payments.py`, `folio.py`, `analytics_reports.py`, `nfc*.py` | OWNER/MANAGER and explicit cash exceptions, KGS/accounting totals, tenant/property bounds | settlement, NFC hardware and acquiring not verified. |
| Staff/operations | `staff_control.py`, `operations*.py`, `staff_guest_requests.py`, `staff_task_reports.py` | manager/owner gates, task assignment/status/history, room-state manager gate | notification/Telegram/voice delivery not verified. |
| Inbox/channels/AI | `inbox.py`, `whatsapp_connection.py`, `channel_outbound.py`, `channel_reservations.py`, `marina_assistant.py`, `ai_sales.py` | capabilities before action, assignment and module gates, inbound/outbound separation, staged imports | WhatsApp, OTA/TTHotel and AI provider connectivity not verified. |

## Test evidence and mandatory acceptance

Existing static/contract evidence includes `apps/mobile/__tests__/*` (navigation, roles, auth/session, booking, dining/kitchen, finance, writes, shared auth, i18n) and focused Python guards under `scripts/test_marina_*.py`, plus `scripts/test_channel_reservation_contract.py`, `scripts/test_guest_property_context.py`, `scripts/test_kitchen_e2e_target_guard.py`, and `scripts/test_season_period_pricing.py`. Presence is evidence of intended contracts, not a statement that they passed in this audit.

Before any visual phase is accepted:

1. `npm run design:fl2:audit` remains green and any intentional inventory change updates source, both design documents, tests, and the guard in one reviewed change.
2. All relevant existing client/server tests pass without deleting, skipping, weakening, or snapshot-updating away behavior.
3. Role × module × property negative paths are exercised; 401/403/404/409/422/503 and unknown mutation outcomes remain visible and safe.
4. RU/KG/EN and light/dark visual QA covers compact and wide layouts; no untranslated fallback may hide an operation.
5. Physical Android E2E is required before release. Until recorded: **Android E2E NOT VERIFIED**.
6. Live integration checks are separately authorized and recorded. Until then: **LIVE NOT VERIFIED**.
