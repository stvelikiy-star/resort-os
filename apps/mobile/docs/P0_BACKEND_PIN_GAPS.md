# Mobile app ↔ backend source pin (03.11.2026)

**Mobile branch base:** `8476b0f4d10e6b33fc45b192d2323c9ca595b2e0`. This is the exact repository tree used by the mobile PR design, NOT the separate full-platform integration branch. Backend source blobs for 14 modules are pinned in `scripts/verify-backend-contract.mjs`. A changed blob causes a CI failure until an explicit reviewed contract update.

- 30 real backend route decorators verified statically: auth, ops, staff, dashboard, reception, PMS grid, booking preview/commit, Inbox, kitchen, dining, assistant, check-in/out.
- 3 required HOLD routes are **BLOCKED**: there is no `services/api/app/pms_holds.py` in this mobile branch tree. The feature exists in a separate backend snapshot and must be introduced by the platform team with migrations and E2E; NEVER copy that server module into mobile PR.
- CI default: inventory and typed tests pass while BLOCKED routes are reported. Production gate: `MARINA_MOBILE_RELEASE_GATE=strict node scripts/verify-backend-contract.mjs` must fail if HOLD is missing.
- Router existence is not proof of response schema correctness or endpoint availability on a deployed hotel. Live integration tests are still mandatory.
- The old checker verified only 11 routes and printed a literal slash-n; this revision fixes both limitations.

**Change control:** the platform team must publish the next verified backend SHA and migrate it into an approved integration branch. No mobile-only developer should change core API/database source.
