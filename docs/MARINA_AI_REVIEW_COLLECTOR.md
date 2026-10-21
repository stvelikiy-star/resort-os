# MARINA SMART — AI Review Collector / Guest Reputation

Status: first stage implemented in PMS source; **external WhatsApp automation NOT enabled**.

## Existing foundation reused
- `GrowthControlBoard`, `growth_control.py`, `guest_engagements` and history-based post-stay candidates.
- Per-property MARINA hotel rules/knowledge JSON now stores approved public review links.
- NPS 0–10 remains independent from **starRating 1–5**. Do not convert between the two scales.

## Employee workflow
1. After confirmed CHECKED_OUT, the guest appears in the post-stay candidate list. Staff creates one internal feedback task (duplicate guard per reservation); due today.
2. Staff requests a candid **1–5 star** satisfaction score **only through an approved channel** with appropriate consent and provider/template requirements. No provider is connected by this feature.
3. An owner/manager records the actual score and optional guest feedback in Growth Control.
4. **1–3 stars** → existing task status IN_PROGRESS, due immediately, first in priority queue, requires owner/manager follow-up. A negative NPS score also retains recovery state.
5. **4–5 stars** → feedback task DONE if no unresolved negative NPS; positive satisfaction never closes an unresolved complaint from the other scale.
6. Public Google/2GIS/Yandex review links **must be offered neutrally to ALL eligible guests irrespective of rating**; guests can share negative or positive experience.
7. Never offer a discount, voucher, gift or privilege in exchange for an external review, positive comment or editing/removing a negative review.
8. A 10% repeat-stay loyalty offer, if added later, must be **independent of rating or public review** and depend on lawful marketing consent and hotel discount limits.

## Guardrails
- No provider-side send, automatic WhatsApp QR, no review-posting impersonation or platform account scraping.
- Hotel boundaries resolved by authenticated property code; public review URLs are configured in that hotel's knowledge only.
- Idempotent task creation per reservation. Public review links are **not gated by satisfaction**, nor conditionally hidden for dissatisfied guests.
- Guest complaint text and phone numbers must remain protected in staff roles; do not send PII to external review platforms.
- Reviewed SQL migration `zz109_marina_review_stars_20261022`: separate nullable column and database CHECK on 1–5 for post-stay feedback.
- Check full database migration, Growth Control E2E, TypeScript, and browser acceptance before Ubuntu deployment.

## Remaining product work
- Template approval/opt-in and unsubscribe mechanism for real WhatsApp collection, with one hotel-bound number per property.
- Reliable checkout event processing: outbox/worker, idempotency key, delayed retries, manual handoff, provider delivery status. **No automated send until tested**.
- Manager SLA tracking/alerts, guest feedback conversation linking, and optional QR on receipts.
- Explicit public review links with host validation and per-provider verified destination.
