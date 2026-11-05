# MARINA SMART — P0 progress and launch gaps, 2026-11-05

## Current candidate and evidence

- Integration: Draft PR #367, branch `marina-smart/integrate-main-rc8-20261105`, not merged.
- Tested application source: `54b126fa8fdd1ed3ccc9d79e803f5919b906dd09`.
- Complete GitHub pull-request workflow pagination: **107/107 SUCCESS**, no failed or pending runs. Earlier reports of 100 runs covered the first page only.
- Machine-readable evidence: `release/marina-smart-integration-candidate.json`; each workflow has its run ID and URL.
- These results prove isolated test behavior, not an external deployment or commercial readiness.
- This documentation update does not transfer the source SHA's CI results to a later application revision.

## Accepted in isolated staging

| Surface | Verified result | Evidence / remaining boundary |
| --- | --- | --- |
| Auth / hotel isolation | Twelve role identities per synthetic hotel; browser role/resource denials and revoked sessions | Authentication is not acceptance of every operational workspace |
| RECEPTION booking | Published hotel-local CORE_RATE preview/commit; privileged override 403, foreign resource 404, duplicate 409 | Existing canonical API and additive shared reception page; external acceptance pending |
| RECEPTION cash | Opted-in CASH-only internal receipt, balance limit and idempotency; no bank/card/backdating privilege | Operator-recorded receipt, not bank settlement; staging-only guard |
| COOK / WAITER | NEW → ACCEPTED → COOKING → READY → assigned WAITER SERVED in two hotels | No automatic payment; role 403, foreign 404, replay 409, logout 401 |
| AGENT | OWNER-only active same-hotel agency binding, core-rate booking, revocation and isolation | Disabled/unlinked agencies denied; foreign guest PII masking preserved |
| AGENT grid correction | Existing canonical grid validates ACTIVE agency and matching property | Aligns calendar access with booking checks; no new API or migration |
| MAID / TECHNICIAN | Shared Staff browser report lifecycles, inspection RBAC, replay denials and hotel switching | Full target operational acceptance still required |
| Third hotel | Additive onboarding CI SUCCESS | No claim of real customer onboarding |
| Guest / WhatsApp / AI | Guest QR, Inbox, RC6/7/8 and hotel knowledge CI SUCCESS | Real provider delivery, real guest financial lifecycle and live AI handoff remain unaccepted |

Concrete browser evidence: [HTTPS Compose run 41998581749](https://github.com/stvelikiy-star/resort-os/actions/runs/41998581749), job `127147812542`.
Its successful logs explicitly record AGENT owner binding/booking/revocation, owner/reception bookings and cash idempotency, COOK-to-WAITER handoff, and shared Staff reports on two hotels.
Source-lock workflows and all other run references are recorded in the integration evidence JSON.

## Historical lock clarification

`release/marina-smart-current-candidate.json` is the **historical RC2 source lock**, despite its filename.
`scripts/marina_candidate_truth_guard.py` pins its PR #314 identity and reviewed source.
`scripts/marina_rc3_source_gate.py` explicitly treats RC2 as immutable and preserves RC3 source/migration locks.
Do not rewrite those manifests, their guard expectations, frozen source blobs or existing migration SQL to update the integration description.
The separate integration evidence file describes #367 without changing any production authorization.

## Remaining blockers

| Block | Required acceptance |
| --- | --- |
| Remaining workspaces | Complete STORE_STAFF, DINING_STAFF, CONTENT_MANAGER and BEACH_PARTNER scope against existing canonical handlers; verify authorized work and foreign-resource denial |
| Guest operational cycle | Prove request → assigned staff → execution → guest-visible result; separately accept any order/folio/charge path with actual accounting behavior |
| WhatsApp | Real incoming/reply/delivery receipts, reconnect, replay safety and two-hotel instance isolation |
| MARINA AI | Hotel-specific knowledge, role permissions and handoff to a human in the target environment |
| External integrations | Record real outcomes for each launch-required OTA/payment/other connection; a synthetic CI result is insufficient |
| Target Ubuntu | Permanent HTTPS, monitored services, backup, separate restore, rollback and final target smoke |
| Final release | One final version, mandatory CI and evidence-based PASS/FAIL protocol; production remains NO-GO |

## Approved order of work

1. **Documentation reconciliation:** record the tested application source and evidence; preserve all NO-GO flags and historical locks.
2. **Workspaces and guest operations:** inspect existing role contracts, close missing operations, then run focused role and two-hotel browser/API/DB tests.
3. **Live WhatsApp and MARINA AI:** accept provider delivery, hotel knowledge isolation and human handoff.
4. **Launch-required integrations:** independently verify each required external connection.
5. **Target Ubuntu:** accept HTTPS, backup/restore/rollback and monitoring.
6. **Final acceptance:** bind the release protocol to one final version and decide GO/NO-GO from actual evidence.

No manual reruns of already-green suites are needed for this documentation correction.
Subsequent application changes require their own targeted tests and mandatory exact-version CI.
DEMO, `apps/mobile`, customer data, Ubuntu services and `main` are outside this documentation change.
