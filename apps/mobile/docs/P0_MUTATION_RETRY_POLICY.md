# P0 mobile mutation uncertainty — checked on 03.11.2026

Scope: app code only. No server idempotency or durable recovery endpoint is invented.

After a server POST/PATCH/DELETE, **OFFLINE, UNKNOWN, HTTP 5xx, and malformed response must be treated as potentially committed**. Keep the exact action locked for the current screen instance and direct the employee to inspect the real PMS/task/Inbox list. Never show "operation failed" and offer an immediate retry.

Allowed retry only after an explicitly rejected HTTP 4xx response (BAD_REQUEST, CONFLICT, FORBIDDEN, UNAUTHORIZED, RATE_LIMIT, NOT_FOUND), and only after correcting the cause. This is a client-side safety fallback, **not** a substitute for server idempotency. Attempting again from a new screen or a second device is still possible and requires server-enforced per-operation idempotency keys, a property-scoped result lookup, and E2E loss-of-ack tests.

Protected surfaces in this PR:
- Maintenance request form: uncertain POST is locked, no duplicate submission on same form, explicit "check task list".
- Reservation check-in/out: ambiguous result locks repeat actions on this screen.
- Inbox claim/status/internal-note: ambiguous mutation locks buttons; no duplicate internal note.
- Booking commit and HOLD: existing fail-closed behavior now shares classification. HOLD remains feature-disabled against pinned backend; do not expose it.
- Demo flow explicitly tests both ambiguous failure (one request) and definitive validation rejection (retry allowed).

Next required platform-only contract: `Idempotency-Key` on reservation commit, financial transactions, operational task create/transition, and Inbox notes; return original result on replay, bind property/user/intent, and log deduplications without PII. Server rollout is a separate authorized change.
