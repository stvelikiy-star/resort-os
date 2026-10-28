# MARINA SMART · QR Guest OS + Reputation + KÖL (2026-10-22)

## Confirmed existing entry point
Actual site page: `apps/web/app/g/[token]/page.tsx`. It mounts the live `GuestConciergeRuntime`, housekeeping policy and on-property marketplace. Guests enter by PERMANENT room QR, then verify a stay PIN. Room QR alone is NOT a guest identity.

## Implemented in this branch
1. `GuestStayReview` on actual QR page supports RU/KG/KZ/EN private 1–5 guest satisfaction during **ACTIVE verified stay**. One record per stay, editable by same authorized guest session; protected by server-side room/assignment/stay/session lookups. No public guest data without PIN.
2. Separate `guest_stay_reviews` table and hotel-scoped `GET/PUT /api/v1/guest-os/rooms/{token}/review`; no second CRM. The existing `guest_crm` history exposes the review against its stay.
3. Growth dashboard lists reviews from the QR room cabinet and ranks negative experiences first. Owner/manager access only. Do not equate it to an independently completed manager follow-up.
4. Approved Google/2GIS/Yandex links come from **this** hotel's rules via verified guest session. All ratings receive the same links. No gift/discount tied to public reviews; no automatic outbound.
5. Guest QR page includes a visible KÖL product area marked **not connected**. It does not accept/pay for orders or claim to know KÖL inventory.

## Important security and product boundaries
- QR stays physically in room; guest session is revoked on checkout. **A checkout-day survey after actual check-out cannot reuse that room QR session.** Future post-checkout review must use a new signed, single-use/expiring feedback link bound to guest+stay, no guest OS access.
- Guest QR feedback is distinct from legacy post-stay NPS and staff-entered stars, which must remain distinguishable in analytics.
- 1–3 stars are surfaced as **manager attention required**, but assigning, resolving, and notifying managers automatically needs its own audited issue workflow and tests.
- Avoid printing guest contact/identity in public KÖL deep links. Do not transfer room QR, session cookie, PIN, stay or reservation IDs to KÖL.
- A KÖL service order will be negotiated by versioned contracts: authorized order intent + consent, service catalog, geolocation only when explicitly needed, price quote, provider availability, payment status, cancellation/idempotency, and transaction/webhook reconciliation. Only final order status returned into hotel's guest OS.
- KÖL stays a separate project/data domain. MARINA SMART owns hotel stay, staff tasks, CRM, consent, and hotel charges; KÖL owns delivery/order fulfillment and courier flows.
- Partner apps must be OPTIONAL, owner-enabled per property, and have graceful fallback when down.

## Next release gates
- Apply migrations `zz109` and `zz110` on disposable PostgreSQL; validate release_contract and backup/restore.
- Run dedicated QR review checks, web TypeScript, Guest CRM CI and a live browser scan with PIN on an isolated test hotel. Test revoked/out-of-property QR, logout, multiple guests, concurrent saves, 1–3 vs 4–5 ratings.
- Verify no leaks between two isolated hotel deployments.
- Build post-checkout signed review link separately; do not weaken existing QR/PIN invariant.
- Connect real KÖL only after API discovery, domain contract and E2E without sharing secrets or PMS access.
