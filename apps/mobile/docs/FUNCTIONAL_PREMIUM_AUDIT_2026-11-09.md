# MARINA SMART MOBILE — functional and premium UI/UX audit
Date: 2026-11-09
Reference mobile base: `35be1a585d5701272e2a9e6a89cbb75cbafa2b01`
Status: mobile-only design/function audit; acceptance work, not commercial release

## Product invariants
- One mobile customer = one assigned property; staff do not select/switch hotels.
- Mobile is an operational companion of the **same PostgreSQL-backed platform**, not a separate source of truth.
- Authoritative writes require live server ACK/readback. Preserve 403, 409, 503, unknown-write journaling, role grants and origin trust anchors.
- DEMO, synthetic QA, RC, hotel01 and production remain distinct.
- Never invent room inventory, category, occupancy, pricing, rates, availability, revenue, guests or meal portions.

## Source evidence
- Live mobile E2E in isolated `marina_mobile_e2e_20261109`: reservation ownership, meal entitlements, kitchen, waiter TABLE orders, agent service, MAID and TECHNICIAN tasks PASS.
- Mobile CI HEAD `35be1a58`: 10 workflows PASS; Android preview compiled. Physical Android E2E is NOT yet signed off.
- Current disposable QA has synthetic rooms (`Mobile QA`, `Agent QA`, `Synthetic Guest Room`); do not represent as actual Three Crowns inventory.
- `knowledge/06_THREE_CROWNS_MASTER_SPEC.md` §10 calls for week/month calendar, property/floor/type/state filters, room assignments and audited writes; §25 explicitly forbids guessed room numbers, types, rates and capacities.
- `docs/THREE_CROWNS_MANAGEMENT_GUEST_KITCHEN_AUDIT_2026-09-05.md` establishes guest requests, kitchen order lifecycle, role restrictions and PMS transaction authority.

## Phase 1 changes in this Draft PR
1. Shared `BrandLockup` ensures MARINA approved logo alignment on onboarding/login.
2. PMS grid shows **server supplied room code + actual name or category + current operational state**. Denser row remains legible.
3. OWNER occupancy is **unknown**, not a fabricated 0%, when there is no valid room denominator.
4. All changes under `apps/mobile/`; no API, migration, DEMO or production writes.

## Role acceptance matrix
| Role | Mobile minimum | Verified | Remaining |
| --- | --- | --- | --- |
| OWNER | Live occupancy/arrivals/departures, finance summary, PMS, staff, tasks, quality alerts | Core/dashboard REST, finance-gated UI | Phone-level tests; drilldown; avoid fake zeros |
| MANAGER | PMS editing/preview, schedule/CI/CO, task assignment, kitchen/meal exceptions, finance with grants | Live roles + booking/ops E2E | Cross-module quick actions; shift brief; permissions regression |
| RECEPTION | Free-cell booking, guest card, check-in/out, meal plan, room readiness | Booking, check-in, entitlement→COOK E2E | True availability filters, quick guest search, manual handoff for dirty room |
| MAID | My tasks, claim, inspection/report, room state, photos if server supports | Task claim→inspection, management approval E2E | Photo only after authorized upload contract; offline safely read-only |
| TECHNICIAN | My tickets, claim, repairs, room blocks, close with proof | Maintenance task flow E2E | Attachments/checklists if server-supported |
| COOK | Arrivals/portion demand, daily menu drafts, orders, status NEW→ACCEPTED→COOKING→READY | Portion snapshot, kitchen status E2E | Menu approval workflow, demand reconciliation and sold-out only with server APIs |
| WAITER | Tables, guest count, menu order, kitchen readiness, claim/serve handoff | Table/order creation, kitchen receipt E2E | Separate authorized serving flow; waiter is **403** on kitchen status patch |
| AGENT | Own availability/booking, extras/service, own status | Booking ownership, TRANSFER, 409 duplicate, cross-agent 404 E2E | Readback/idempotency endpoint; manual pending reconciliation |
| STORE_STAFF | Goods, stock movement, replenishment, authorized cashier | NOT SERVER-VERIFIED | Server contracts first. Keep LIVE screen fail-closed. |

## Premium visual system
- Existing brand: navy/teal, champagne gold, white; preserve approved MARINA logo. Never create a new random mark.
- Establish a single icon family (lucide), 20–24px regular, 1.9–2.2 stroke; 48–56px touch targets. Restrict icons to actions they accurately represent.
- Header: consistent logo baseline, title, subtitle, aligned profile/status; don't scatter decorative labels.
- OWNER grid: fixed two-column alignment, consistent card heights, no mixed static demo/real KPI. Empty/unverified metrics show `—` and an explanation, never zero.
- PMS: actual category/name shown alongside room code; free tap = preview and explicit booking, occupied tap = reservation card; preserve week scroll and booking conflict checks.
- Soft animations: 120–220ms press/tab, 260–350ms cards and bottom sheets; honor reduced-motion setting; no animation on destructive confirmation that hides feedback.
- Responsive phones, dynamic font scale, overflow/wrapping and safe areas verified on physical Android.
- Translate every role, status, warning and failure RU/KG/EN. Test long Kyrgyz strings; no raw API strings shown as localized labels.

## Comparable product research (official sources; ideas, not copied UI)
- Cloudbeds app: quick guest/reservation search, today/tomorrow arrivals/departures, guest notes and housekeeping actions. https://myfrontdesk.cloudbeds.com/hc/en-us/articles/21011188971035-Cloudbeds-App-Overview
- Mews Operations: task-first room operations and room/guest linkage, backend workflow boundaries. https://help.mews.com/s/article/Mews-Operations
- Little Hotelier: single calendar, fast check-in/out, real-time device sync, pricing and payment quick actions. https://www.littlehotelier.com/mobile-app/
- Hotelogix: mobile dashboard, operational room state, tightly controlled offline/online data flow. https://www.hotelogix.com/hotelogix-mobile-pms

## Next implementation gates
P0-A: Accept ONE known SHA + physical Android login; record screenshots across narrow/wide and reduced-motion.
P0-B: Replace synthetic QA room inventory with **clearly named fixtures** for controlled tests, and separately load actual customer room roster only after verification. Example `№ 1 — Спальный` is a fixture, not a Three Crowns fact.
P0-C: Complete owner/manager/reception booking & meal snapshots and RBAC regression on current server, without bypassing 503/403.
P0-D: Confirm waiter serving contract and agent service idempotent readback server-side before exposing more mobile actions.
P1-A: Premium header/icon audit, owner symmetry, PMS category filters (only if available in API), graceful skeletons and success/unknown states.
P1-B: Complete RU/KG/EN string audit including accessibility labels; physical device animations and tests.
P2: Notifications, attachments, store, OTA/WhatsApp enhancements only with confirmed authorized endpoints and separate business approvals.

Commercial status: NO-GO until same-SHA CI, independent database restoration, physical Android role journeys, production HTTPS/certificate and backup/rollback evidence are all PASS.
