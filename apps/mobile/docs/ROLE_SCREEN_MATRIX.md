# Mobile ↔ Web role and operation inventory — 15 November 2026

Source base: `86758c54b2e6752fc5c2edb3925e729bf1c3d6c5` (Draft #522). Kitchen Operations and real HTTPS Staff browser cycles PASS; overall Android completion must be checked independently. Last fully green checkpoint recorded here: #521 `b3bd4a9c` (35 workflow runs SUCCESS). AGENT changes below are inherited from #519/#521; this follow-up adds technician reports and OWNER/MANAGER draft publication. This document supersedes the previous navigation-only inventory. **Source parity is not device or live E2E acceptance.** Every operational role remains PARTIAL until the same-version runtime scenario passes.

Sources: `src/roles/registry.ts`, `src/api/realApi.ts`, `src/api/liveModules.ts`, mobile routes/components; `apps/admin/components`, `apps/staff/components/StaffRoleGateway.tsx`, `services/api/app`. UI permissions never grant server authority. One hotel per customer app; no hotel-switching requirement is introduced.

| Role | Mobile screens / implemented operation groups | Web counterpart | Confirmed remaining difference or gate |
|---|---|---|---|
| OWNER | Overview; PMS; Inbox; Kitchen; Team; tasks, rooms, requests; Finance from Overview; meal plans from PMS; Profile | Admin dashboard/PMS, HotelFinanceBoard, GuestServicesCenter; Staff kitchen and operations | Finance is recorded receipts, obligations, settlements and kitchen costs, not recognized profit. Recipe editing and procurement controls already exist; draft recipe approval is now also exposed to OWNER/MANAGER. This follow-up adds explicit draft dish publication with a chosen price for OWNER/MANAGER; COOK remains draft-only. Acceptance on the new SHA is pending. Full staff/access administration, wider Web reports and settings are not mobile parity. |
| MANAGER | Overview; PMS; Inbox; Kitchen oversight/recipe controls; Team/task assignment; rooms/requests; Finance summary; meal plans; Profile | Admin PMS/reception; Staff kitchen/operations; finance summary | This follow-up exposes draft dish publication and recipe approval; full Web configuration/staff access administration absent. OWNER expense ledger is deliberately OWNER-only. |
| RECEPTION | Reception list/detail; check-in/out; booking preview/commit; PMS; guest-request claim/complete; Inbox; meal plans; Profile | Admin reception/PMS/GuestServicesCenter and Staff GuestRequestShiftPanel | General guest-service creation, guest PIN/QR administration, full folio/payment tools and Web booking-management scope not all implemented on mobile. Date changes deliberately remain OWNER/MANAGER. |
| MAID | Tasks, Rooms, Profile; claim, housekeeping checklist/report, inspection handoff | StaffShiftV2 / housekeeping | No photo attachment flow; complete shift, checklist, room-state and session-revocation device acceptance pending. |
| TECHNICIAN | Tasks, Requests, Rooms, Profile; maintenance creation, claim and, in this follow-up, a meaningful repair completion report through the canonical complete-report endpoint | StaffShiftV2 / maintenance | No photo attachment flow; complete incident/room-state and session-revocation device acceptance pending. |
| COOK | Kitchen, Dining, Profile; queue/status; menu drafts; production targets and fact portions; recipes; ingredient need; stock consumption; losses; procurement request; production snapshots | Staff KitchenAdmin/KitchenIngredients/Kitchen procurement | Role correctly cannot publish manager-only menu. Recipe/stock/production atomicity and complete device cycle still require acceptance; navigation and authoring are not equivalent to all Web kitchen controls. |
| WAITER | Dining, Profile; tables/menu; table creation; authentic stay seating; order with quantities; waiter assignment; serve; room-folio posting; move and release seating | Staff dining floor, KitchenAdmin, seating/folio tools | Full device acceptance pending. Seating cancellation and some floor administration are not exposed. Folio creates a charge, not a received payment. |
| STORE_STAFF | Store, Profile; canonical stock list and direct receipt | Staff StoreStaffStock | Procurement request/receipt and losses are already mounted in Store via KitchenProcurement/KitchenLosses. Direct stock receipt has been fixed in #522 across API/Mobile/both Staff forms: persisted ID, 409 payload conflict, lost-ack/restart/concurrency and real browser/PostgreSQL verification PASS. This follow-up adds durable procurement REQUEST/RECEIVE journals and explicit restart replay; dedicated PostgreSQL/process acceptance is pending. Direct receipt tests do not prove every stock write. This corrects the earlier false missing-workflow statement. |
| AGENT | PMS, Profile; own linked organization preview/commit; six services after booking and, in this branch, from own existing booking preview | Shared agent booking; canonical guest-service queue for receiving staff | Baseline service POST rejects ordinary AGENT: fixed in this branch with ACTIVE link + own reservation checks. General queue stays denied. This follow-up adds service date/time/note and scoped own-reservation status readback. The common hotel queue remains denied; unknown outcomes still require explicit review (a matching list entry does not prove delivery of a particular attempt). No HOLD, manual price or arbitrary discount. |
| DINING_STAFF | Profile only in LIVE | Legacy StaffRoleGateway recognizes role | No reviewed mobile workspace; blocked, must resolve legacy-role support explicitly before claiming all-role parity. |
| CONTENT_MANAGER | Profile only in LIVE | Admin site/content/media | No reviewed mobile content workspace; blocked. |
| BEACH_PARTNER | Profile only in LIVE | No counterpart verified in this audit | No reviewed mobile workspace or verified Web operation contract; blocked. |

GUEST is not a staff `Role` enum value. Guest OS has separate authentication and remains a separate acceptance surface.

## Operation checklist

| Operation | Mobile implementation | Canonical Web/API evidence | Source status / runtime requirement |
|---|---|---|---|
| Booking grid and free-cell → preview/commit | `(app)/pms.tsx`, `new-booking.tsx` | Admin PMS; `main.py`, `pms_reservation_create.py` | Implemented; lost-ack journal retained |
| Occupied-cell → booking preview/detail | `PmsBookingSheet.tsx`, `reservation/[id].tsx` | `reception_reservations.py` | Staff detail implemented; AGENT own preview uses scoped grid only, no staff detail grant |
| Date changes | `reservation/[id].tsx` | `reservation_schedule.py` | OWNER/MANAGER single-room preview/commit only |
| HOLD | `holds.tsx` | `pms_holds.py` | Route exists; PMS entry feature flag false, not normal-navigation parity |
| Check-in/out | `reservation/[id].tsx` | `stays.py` | Implemented; physical cycle pending |
| Reception guest-request claim/complete | `(app)/reception.tsx`, liveModules | `staff_guest_requests.py` | Implemented, not full GuestServicesCenter authoring |
| Task assignment / housekeeping / maintenance | `realApi.ts`, task/admin screens | `operations.py`, `operations_assignment.py`, `staff_task_reports.py` | Implemented; photo gap remains |
| Meal-plan guest entitlements | `meal-plans.tsx` | `dining_stays.py` | Implemented; same PostgreSQL E2E required |
| Cook dishes and planned/prepared quantities | `KitchenDrafts`, `KitchenProductionPlanner` | `kitchen_menu_management.py` | Draft publication for OWNER/MANAGER added in this follow-up; physical acceptance pending |
| Recipe and ingredient demand | `KitchenIngredients` | `kitchen_recipes.py` | Implemented with DRAFT/APPROVED and sample exclusions |
| Procurement / stock / losses | `KitchenProcurement`, `KitchenStockMobile`, `KitchenLosses`, Store | `kitchen_procurement.py`, `kitchen_stock.py` | Role-dependent coverage; direct receipt retry/unknown-outcome gap above |
| Waiter full service | Dining, `DiningServiceMobile` | `kitchen.py`, `dining_seating.py`, `dining_folio.py` | Implemented subset; no blanket device PASS |
| Agent additional services | `AgentGuestServices` reused from new booking and own PMS preview | `guest_services.py` POST | Narrow creation + scoped status readback in this branch; no charge/payment creation |
| Finance / OWNER expenses and settlements | `finance.tsx`, `OwnerExpenses` | `hotel_finance.py`, `owner_expenses.py`, `owner_cash_reconciliation.py` | Implemented records; expense VOID UI and recognized profit absent |
| Content / beach / legacy dining | no LIVE workspace | Needs reviewed contract | BLOCKED |
| AI / WhatsApp provider acceptance | Existing source retained | Existing integrations retained | Excluded from this task; no connection or provider test performed |

## Acceptance still required

For each enabled role: login → permitted read → permitted write → Web readback → PostgreSQL row → logout/restart/network loss/access revocation. Run on one immutable candidate SHA and one disposable PostgreSQL database. Prove denied actions create no row. Expo Web screenshots and APK compilation are separate evidence from physical Expo Go/Android execution.
