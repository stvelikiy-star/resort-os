# MARINA SMART P0 — HOLD TTL two-hotel acceptance, 2026-11-05

**Scope:** MARINA SMART main shared platform, continuation of consolidated RC3–RC8 Draft PR #363. This is a narrow acceptance-only change. No customer data, production secrets, DEMO, Ubuntu, `apps/mobile`, new migrations, or merge.

## What is already accepted upstream

- On PR #363 HEAD `b2aa073a94c7185ea00b4d09bbbd558f793429b3`, 87/87 GitHub Actions passed. The existing browser+PostgreSQL suite `scripts/marina_shared_live_browser.mjs` / `scripts/marina_shared_live_browser_db.py` tests two independent hotels: bookings, changing dates, HOLD creation and manual release, manual cash payments, cancellation, check-in/out, room repair, maid inspection, role enforcement and post-operation database/audit truth.
- `scripts/marina_shared_role_auth_ci.py` covers all 12 server role identities in two hotels, while `scripts/marina_shared_staff_lifecycle_ci.py` covers **six owner-assignable** managed roles, lifecycle/revocation and same-name isolation. Do not confuse six managed roles with all twelve being owner-createable.

## New P0 acceptance added here

The existing HOLD contract checks timestamp and exclusion-index presence, but the integrated browser suite retires HOLDs manually. The new `scripts/marina_shared_hold_ttl_two_hotel_ci.py` operates through the **canonical FastAPI app** with disposable real PostgreSQL to verify:

1. Owners A/B create separate 60-minute HOLDs with the same local room dates; repeated/overlapping HOLD is 409, foreign room/hold IDs 404, non-owner operations 403, anonymous 401.
2. Advance the stored timestamps of **only HOTEL_A** to represent an expired hold without sleeping or changing system time; respect the immutable database check `expiresAt > createdAt`.
3. A's expired hold cannot be converted into booking (409); A's inventory is sellable again, but HOTEL_B still owns its untouched active HOLD and still blocks booking.
4. Expire B separately; both inventory blocks are retired. A repeated shared worker sweep must be idempotent and no booking or payment should appear.
5. The CI requires exactly the PR head SHA, frozen RC3 source verification, existing Prisma migrations and localhost-only synthetic database guards.

This is **synthetic acceptance, not a real production 60-minute wall-clock observation**. Production is NO-GO pending external staging, operations and real provider acceptance.

## CI scope and isolation

The first test-only branch `test/marina-main-p0-two-hotel-hold-ttl-20261105` triggered an unrelated Three Crowns staging gate, despite passing its core P0 test. The final reviewed branch `marina-smart/main-p0-two-hotel-hold-ttl-20261105` uses the repository's existing MARINA-specific pull-request workflow routing. No unrelated Three Crowns CI or code was modified or bypassed.
