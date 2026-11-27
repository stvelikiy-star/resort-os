# ASKA TASH GREEN API — readiness and pilot choice

Scope: existing ASKA_TASH single-property installation. No provider credentials, external message sending, real guest data, or production changes during preparation.

## Verified offline evidence
Exact source baseline f4deb91ffc7b837db557bcf1282f48fbba02bdb1. Existing tests executed in disposable Docker containers with network disabled and no provider configuration: marina_green_poll_test.py 9/9; test_marina_single_hotel_whatsapp_capabilities.py 3/3; test_marina_whatsapp_connection.py 10/10; test_marina_whatsapp_reception.py 4/4. Total 26/26. These are synthetic tests, not a verified live account, provider delivery or database-backed end-to-end receipt.

## Decision
Prefer the existing embedded single-property connection and protected Inbox adapter; do not duplicate the Three Crowns n8n automation. The current single-property polling adapter supports limited direct text receipt, verifies instance/property binding, and acknowledges a notification only after Core success. Canonical ingest includes property-scoped idempotency and external message identifiers. Unsupported notifications stop processing for manual reconciliation; do not acknowledge unreviewed media/status/group events. Queue retention and reconnection monitoring are required.

Important boundary: RC7 webhook configuration expects at least two shared adapter bindings, and is designed for shared staging; it is NOT a single-property ASKA_TASH production webhook. Single-property outbound capability currently fails closed without an approved adapter (covered by the tests). Do not claim full WhatsApp functionality or enable shared preview to force connectivity. A separate reviewed single-property webhook/outbound implementation with independently authenticated provider events, durable dedupe and reconciliation is still required for a complete launch. QR pairing/status alone does not prove delivery.

## Next work
1. Confirm owner-approved independent ASKA_TASH number and Green instance; secret values only in protected server configuration, never in Git/chat.
2. Review single-property adapter and owner pairing in a synthetic environment. Add a reviewed single-property ingress and outbound authorization boundary, independent secret, property identity, durable duplicate/replay handling, and delivery-status reconciliation. Reject unsupported events without silently losing them. Use existing canonical Inbox, not a second data store.
3. Obtain explicit owner permission for provider connection and isolated controlled test number. Verify receive, replay, invalid credentials, wrong instance, disconnect, outage, retries, duplicate outbound request and unknown delivery outcomes. Do not process real guest messages as test inputs.
4. Keep AI draft/human approval initially, verified property facts only; no guessed prices/availability/policies, confirmed reservations or payments. Review staff access, human handoff and operational alerts. Do not enable auto-send until separate approval and functional proof.
5. Complete approved external HTTPS, R2 restore proof and monitoring. No deployment before specific owner GO.

Current gate: NOT CONNECTED, offline source tests PASS; single-property full webhook/outbound, real instance pairing, external E2E and AI acceptance remain open.
