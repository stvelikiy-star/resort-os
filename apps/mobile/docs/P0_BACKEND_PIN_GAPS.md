# Mobile app ↔ unified Core #428 contract pin (10.11.2026)

**Integration branch:** `feat/marina-unified-rc428-mobile422-20261110`.

**Core source parent (immutable SHA):** `73725dc2fd11ad45a5d9bc23a2c21dd732bd61d7` (PR #428, includes #427 → #426 and the final #425 WhatsApp-capabilities content).

**Mobile source:** `ee17548e5c897f268e0a637e7dfd0d6a301b1f5e` (PR #422), with security regression tests from `1d069cb6f412c5911bfc0e112d9ff34aad788592` (PR #416). These are now incorporated into a **single monorepo SHA**, without copying stale Web, Admin, Staff or Core content from the mobile branch.

`scripts/verify-backend-contract.mjs` pins the **exact Git blob contents of 17 reviewed backend files** from Core #428 and checks **40 static route decorators**, including GET/POST/DELETE HOLD endpoints. Failure on source drift is intentional; do not weaken or bypass the gate. The previously documented three missing HOLD routes are **present in this Core candidate**.

**Scope of this static check:** code provenance, existing declared route paths and method prefixes. It does **not** prove:
- payload/response schema compatibility and server runtime configuration;
- cookie/session renewal, auth revocation and real role enforcement;
- permissioned finance, dining meal entitlements or kitchen order lifecycle;
- inter-hotel isolation or physical Android operations;
- real GREEN-API/AI provider connectivity.

All these require CI and controlled live E2E against the exact combined release SHA and a single persistent test PostgreSQL. The physical Android E2E, remote encrypted backup restore, provider acceptance and production cutover are **NOT VERIFIED**.

**Go/no-go:** keep this release candidate Draft until the required source+mobile+Android workflows PASS and the separate live operational checklist is signed off. No customer/demo/main mutation.
