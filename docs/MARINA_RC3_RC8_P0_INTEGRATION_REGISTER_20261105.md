# MARINA SMART — RC3–RC8 P0 integration register (2026-11-05)

**Scope:** main platform shared multi-hotel, isolated Draft PR only. No release to `main`, no Ubuntu, DEMO, mobile or real data changes. Production remains **NO-GO**.

## Integration decision: ONE GREEN-API provider route

- Canonical upstream: RC3 immutable manifest, RC4 Guest QR #348/#351, shared Inbox RC5 #352, per-hotel AI public knowledge #353, owner QR RC6 #354.
- Canonical GREEN-API RC7: #356 `services/api/app/green_api_webhook.py` plus `shared_green_rc7.py`. It handles BOTH verified incoming text and **tracked outgoing statuses**. This is the dependency required by RC8 #357; `/api/v1/automation/green-api/webhook` must be registered **exactly once**.
- RC8: #357 `services/api/app/green_outbound.py` and existing Inbox `send-text` endpoint, human-operated only. Queue acceptance is **not delivery**. Ambiguous provider outcomes require manual reconciliation, never automatic retry or auto-send.
- Admin human reply UI: #358. Fix its missing `DYNAMIC_FRAGMENTS` object comma, then verify TypeScript and Chromium.
- Owner/Manager/Reception shared WhatsApp entry: #355. Auth logout status is **204**; fix test, do not alter API.
- Guest RC4: integrate ALL five #350 changes while preserving #351 Compose/Chromium test improvements. UI displays ONLY `MAINTENANCE` and `ADMIN` when server says they are available; AI hidden. Shared guest may not cancel legacy paid/charged guest tasks.
- Security: #360 exact 11 negative RC6 binding/URL tests; port #361's active DB tenant/property UUID cross-check, reject duplicate `Authorization`, require JSON, and negative tests INTO canonical #356 webhook. **Do not** copy #361's duplicate `shared_green_rc7_webhook.py` or independent `MARINA_SHARED_GREEN_WEBHOOK_RC7_*` flags. RC7 configuration contract remains `MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON`, `MARINA_SHARED_GREEN_RC7_ENABLED` and explicit `MARINA_SHARED_GREEN_RC7_CONFIRM`.
- #361's corrected `pms-chessboard-ci.yml` server-readiness check is retained to prevent fixed-sleep startup races.
- RC3 manifest critical Git blobs and 39 Prisma migrations are frozen; no DB migrations in this integration.

## Mandatory acceptance before this candidate can proceed

1. **One exact PR HEAD SHA**. All required GitHub Actions on this SHA successful, including Release Gate, shared RC3 source lock, real two-hotel PostgreSQL/Chromium Guest QR, shared WhatsApp browser, RC6 owner QR, RC7 callback (incoming + tracked delivery), RC8 human outbound, finance, RBAC, PMS and Full Stack Smoke.
2. Negative contract: untrusted headers, absent/duplicate bearer, wrong provider instance, stale tenant/property UUID and inactive tenant fail closed. No unknown webhook creates a conversation or falsely marks delivery; repeated webhook is idempotent.
3. Human outbound only: no AI auto-send, no insecure provider credentials in API response. `QUEUED` isn't `SENT` or `DELIVERED`; ambiguous results must not auto-retry.
4. Production switch-off remains default; no real provider/phone/LLM/payment calls in CI. Real GREEN-API message ID and delivery, external HTTPS staging and target-host restore remain **NOT VERIFIED** and block commercial launch.
5. No merge without a separate authorized go/no-go decision and real production staging review.

## Upstream source lineage

RC4 #348 `6b5495245d7859b7dfbff7716ff1047cc13c5e86`; #351 `333db2c1a03aa3801e3f7e1f0ea9c21210011862`; RC5 #352 `51d93a058f9b947fec7558fef86160f5d6975479`; public AI #353 `eb1f77b5cf482a8eb6f18c67d0e4c2cc9afb829c`; RC6 #354 `aebde53b3af62624d299779875a4e3bb484a6a92`; RC7 #356 `654b5a85e2e52751bc632056ab91bad5a149333c`; RC8 #357 `6c210def1b30b8d3ddbb8dbb2d8e777b9bbc9e3d`; UI #358 `8a69e46897de1a7f0ba519629a6f5b3673110caa`.

Parallel safety patches: #350 `27f1479043cb749e78d117687268e2fb8a0284a4`, #355 `9cca50880573cb5f1f0c7d4cd6809fa7fe919b80`, #360 `4827679c5031317d8866d5fcdca38e0e64dadfb9`, #361 `2431404348b7977683096a6ec8b8a87dafe4f41c`.
