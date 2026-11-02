# MARINA SMART — pilot checklist without Green-API (2026-10-21)

**Scope:** one isolated SYNTHETIC hotel `hotel01` on Ubuntu. This is a verification plan, **not** evidence of production readiness. Green-API, OTA, n8n messaging, external payments and AI auto-send remain **OFF**.

## Existing verified source components
- Public website `apps/web/components/BookingWidget.tsx` calls Core check-availability and sends a **ReservationRequest**, not a guaranteed Reservation.
- MARINA Core `services/api/app/main.py`: `GET /api/v1/booking/check-availability` and `POST /api/v1/booking/requests`.
- Admin PMS `apps/admin/components/PMSGridV9.tsx`, preview/commit booking API and canonical grid.
- Owner inbox `apps/admin/components/InboxBoard.tsx` and `services/api/app/inbox.py`.
- Per-hotel rules `apps/admin/components/HotelRulesBoard.tsx`.
- Three-channel domain `services/api/app/communication_ingest.py` with idempotent normalized ingress; provider webhooks **not** live.
- Owner login confirmed by user on local http://127.0.0.1:15001; external Quick Tunnel authorization **not** accepted.
- Current `compose.marina-fleet.yaml` is synthetic/staging and does not deploy production WhatsApp keys.

## Release gates: in strict order
1. **Non-destructive readiness:** `cd ~/marina-smart-demo && python3 scripts/marina_fleet.py status hotel01`; verify all services healthy. Do not use `down -v`.
2. **Local frontends:** admin `http://127.0.0.1:15001`, public web `http://127.0.0.1:15000`, staff `http://127.0.0.1:15002`. Test with browser and synthetic identities; do not enter real guest data.
3. **Owner + staff RBAC:** owner can access permitted modules, disabled roles denied; unauthorized calls return 401/403. Do not share MS/MS01 beyond this disposable demo.
4. **Website request:** on public web, choose dates, fetch availability, send synthetic request; confirm it appears in admin CRM; verify status remains REQUEST, not guaranteed reservation and does not generate payment.
5. **Booking E2E:** admin preview seasonal total; commit a synthetic booking; conflict on same room/dates must fail; confirm grid result. Do not run write-based CI scripts against hotel01 unless they explicitly scope themselves to disposable hotel01.
6. **Rules and AI truth:** owner changes a test rule and verifies MARINA AI does not invent prices, free rooms, charges or payments; no external AI key means its live response is not verified.
7. **Communications:** manual inbox, internal notes, linked ReservationRequest; only provider-confirmed delivery counts as external reply. WhatsApp send/AI auto-send **must not** be represented as operational.
8. **Staging isolation:** independently verify a second disposable hotel using **separate database and app stack**, no cross-hotel users, rates or conversations. Confirm backup and restore on a disposable target.
9. **Public demo:** remove admin/short-password exposure; read-only tour or isolated disposable sessions, rate limits, data reset and explicit demo labels. Do not expose synthetic owner API publicly with MS/MS01.
10. **Permanent HTTPS:** named Cloudflare Tunnel + own domain + verified Access/DNS/OTP/browser cookies. Temporary protected Quick Tunnel currently yields 401 remotely and is **not** production ready.
11. **Payments/OTA/Green:** separate future integrations, no automatic sync or claims of working provider connection until real end-to-end test.
12. **Real hotel:** explicit owner permission, data processing and backup policy, TLS and alerting, restore test, load/capacity test, staffed rollback plan.

## Automated evidence (not a substitute for live browser acceptance)
- Workflow: `MARINA SMART Full Stack Synthetic Smoke` covers synthetic booking and related tests.
- Workflow: `AI Unified Communications CI` covers inbox invariants.
- Workflow: `MARINA Ubuntu Hotel Fleet CI` tests two isolated stacks and backups.
- Workflow: `MARINA Direct WhatsApp Adapter CI` uses offline fake events; **not real WhatsApp**.
- New WhatsApp adapter is unconfigured and dormant; no Green-API account required for these checks.

## Next implementation batches
A. Stabilize public demo and permanent domain/Access without exposing real admin.
B. Full owner/guest/admin browser smoke and website-to-CRM acceptance with synthetic only.
C. MARINA AI live data and safe booking lead qualification, **without external messaging**.
D. Add Green-API or official Meta provider only after pilot passes all above.
