# MARINA SMART · WhatsApp workspace — employee flow (without provider)

**Scope:** UI/staff procedure only. No Green-API activation, no QR, no inbound provider webhooks, no AI auto-send.

## Always-visible navigation
`AdminShell` → **WhatsApp / AI** appears in top-level navigation for OWNER, MANAGER and RECEPTION. It is **not** inside «Ещё».

## Workflow tabs in operational order
1. **Входящие** — actual existing WhatsApp-kind conversations from MARINA CRM only. Staff identify guest, dates and occupancy; internal notes are not sent to guests. The interface must not show seeded/fake provider conversations or imply messages are live.
2. **Заявки и брони** — inspect the request in CRM and prices/availability in PMS; distinguish Inquiry / ReservationRequest / committed Reservation. Never promise reserved inventory based on an inquiry.
3. **MARINA AI** — review existing property rules and allow only factual answers. No automatic external replies while provider is disconnected.
4. **Подключение** — honest status and requirements. QR/activation is a later Green-API/Meta integration, not a placeholder that falsely claims connected.

## Employee role contract (current)
- OWNER, MANAGER: CRM message viewing, status changes, internal notes and link to ReservationRequest, as allowed by current Core endpoints. Outbound WhatsApp **off**.
- RECEPTION: may view only **WHATSAPP** conversations from the authenticated hotel's database, claim a conversation, change its status and add private notes. Existing owner-only request linking, manual assignment and outbound delivery remain unavailable. No other messaging channel may be viewed by reception.
- AGENT: only PMS, never hotel correspondence.
- MAID/TECHNICIAN: operational duties, never guest message Inbox.

## Acceptance / no-hallucination gates
- Ensure the navigation CTA remains top-level and usable on mobile.
- Without providers, status says disconnected; no QR and no fake chats or fake delivery ticks.
- Filtering to WHATSAPP happens in UI for authorized staff. Server still scopes tenant via trusted property ID; never replace that with client-supplied hotel code.
- Reception reading must be enforced by tenant and channel checks in the API; standalone offline RBAC contract tests included in `scripts/test_marina_whatsapp_reception.py`. Verify with a real isolated test hotel before production.
- Test owner/manager real stored test conversations, linking requests, internal notes and role denial.
- Typecheck `npm run typecheck --prefix apps/admin` in CI and test in disposable Ubuntu pilot, not production.
