# MARINA SMART — next workstream gates: guest timeline, Kyrgyz acquiring, cottage navigation
Date: 2026-10-22. Source-based design brief; **not a production implementation**.

## Confirmed reusable modules (do NOT fork these)
- Guest history: `services/api/app/guest_crm.py`, `apps/admin/components/GuestCrmEnrichmentPanel.tsx`.
- Booking and finances: `reservation_payments.py`, `hotel_finance.py`, `reservation_detail.py`, `stays.py`.
- Existing service-point payments: `service_point_payments.py` and `mkassa_payment_bridge.py`. They process **service points**, not hotel booking charges; do not relabel them as booking acquiring.
- Room setup: `hotel_setup.py` owns physical room / building / zone.
- Guest portal: `apps/web/app/g/[token]/page.tsx` and `GuestConciergeRuntime`; room QR alone is not guest identity.

## Unified Guest Timeline — no parallel CRM
Existing guest record owns immutable references to reservation, stay, room assignment, internal task, payment and guest feedback. The UI may aggregate a **paginated** timeline keyed by property+guest and timestamp, with each row linking to canonical source object. Never copy payment amounts or guest documents into generic events. Guest QR review is now stored per stay; legacy NPS is an independent scale. All cross-table joins must include property ID, and every PII read must respect roles.

Recommended initial timeline types:
- BOOKING_INQUIRY, BOOKING_CONFIRMED, PAYMENT_RECEIVED, PAYMENT_REVERSED
- CHECK_IN, CHECK_OUT, ROOM_CHANGED
- GUEST_SERVICE_REQUEST, GUEST_SERVICE_COMPLETED
- PRIVATE_STAY_REVIEW (1–5), INTERNAL_COMPLAINT_OPEN, INTERNAL_COMPLAINT_RESOLVED
- PARTNER_ORDER_CREATED, PARTNER_ORDER_STATUS_CHANGED (later, not yet connected).

## Kyrgyz acquiring: first safe acceptance slice
1. HOTEL-BOUND provider configuration with credentials in backend secret store, unique merchant for every hotel.
2. `payment_intent` identifies immutable property/reservation/request, amount in integer tyiyn, KGS, currency, expiration, source and unique idempotency key.
3. Quote amount and deposit required must come from **server-validated booking and seasonal price**, never AI prose or caller-supplied amount.
4. Provider adapter creates a hosted payment link; it is not a "google search" URL and never contains hotel admin credentials.
5. Webhook signature/transaction lookup MUST verify provider id, merchant, reference, currency, exact amount and state; record event exactly once.
6. Only after database transactional confirmation may finance record the payment; no automatic booking confirmation if inventory/HOLD has expired. Conflicts open staff reconciliation rather than double-booking.
7. Separate fiscal receipt job and status: paid != fiscalized; refunds/reversals reconciled in both systems.
8. All payments and refunds in the canonical guest/reservation finance history; no shadow ledger. Payment services remain OFF without signed bank contract, test keys and verification.

## Resort / cottage wayfinding: low-risk order
1. Add OPTIONAL wayfinding profile per physical room: validated lat (-90..90), lon (-180..180), parking label, building/zone, path video HTTPS URL, written directions (no access credentials).
2. Room map link can be opened from booked-stay details. Before check-in, public navigation must not expose PIN, personal guest identifiers or reservation number.
3. Guest QR session can show personalized room instructions after PIN; future pre-arrival link is short lived and checked against confirmed reservation.
4. Lock PIN, Wi-Fi password and payment links must never appear in generic public map HTML nor in external map links.
5. Admin UX: extend existing physical room editing screen; do not add "Issyk-Kul database" or new hotel role.
6. Acceptance: apartment and multi-cottage hotels, two different hotels, no cross-property coordinates; mobile offline/low-bandwidth fallback.

## KÖL (separate project)
No shared guest database. Signed order intent only after explicit guest consent; pass only required delivery address/time/items; idempotency key, cancellation, safe webhook callback, and user-facing explicit external provider name. Fallback to regular room service if KÖL unavailable.

## Activation sequence
(1) All QR/CRM/migration/reputation CI green; (2) staging browser + room PIN tests; (3) non-destructive Ubuntu deployment after backup/restore proof; (4) implement and acceptance-test room navigation; (5) bank sandbox payment adapter; (6) fiscal and partner connectors.
Green-API and WhatsApp auto-send remain disabled until explicitly enabled and end-to-end tested.
