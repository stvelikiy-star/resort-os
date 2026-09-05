# Three Crowns Guest Marketplace V1

Status: implementation specification for branch `ux/management-kitchen-guest-v1-20260905`.

The in-stay Guest OS remains QR + PIN + HttpOnly session protected. Marketplace features are an extension of that authenticated guest surface, not an anonymous shop.

## V1 sections

1. **Dining now** — published Kitchen menu, quantities, guest count and notes; order goes to the existing Kitchen queue.
2. **AI concierge** — verified hotel facts through the existing fail-closed AI provider boundary. No reservation/payment confirmation authority.
3. **Offers** — transfer, sauna, excursions, billiards and administrator assistance as explicit Guest Service requests that staff confirm.
4. **Optional KÖL bridge** — rendered only when `NEXT_PUBLIC_KOL_MARKETPLACE_URL` is configured. No hardcoded URL or partner guarantee.

## V1 truth rules

- Guest menu = active AND non-draft only.
- Server owns item price and order total.
- Order total is Kitchen operational value and does not automatically create Hotel Payment.
- Offer click/request is not confirmation of availability or price.
- AI uses verified facts; it is not transaction truth.
- No external offer is shown without configured destination.
- Existing general website AI widget stays hidden on `/g/{token}` to avoid two competing assistants.

## Next step

Replace hard-coded offer cards with owner-managed offer records only after a Core/CMS contract exists. Add impression/click/request attribution without storing sensitive guest profiling in the browser.
