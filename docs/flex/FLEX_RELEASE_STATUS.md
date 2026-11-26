# FLEX release status — Stage 0
Roadmap: owner-approved MARINA_SMART_FLEX_MASTER_ROADMAP.md, edition 1.0 (2026-11-25), SHA256 04355f932ebe469e61dc17edf291b4934d182a074fccb2ddf31835a430ec8c93. This status record does not replace or revise the roadmap.
 
## Accepted integration checkpoint
- Branch qa/flex-pilot-20261124; SHA 128ba9e3d88e1a04d21d566a0e230bbfd9a1d07c.
- PRs 611–613 MERGED. Integration workflow snapshot: 42/42 SUCCESS. Catalog/browser run 45661707237, scope/restore run 45661707513.
- Compare against frozen PMS base 2642eedc27431fdb9eaa9f7bf306904d487f4b9c: ahead 423, behind 0, 149 added files, zero outside FLEX allowlist, zero nonadditive files.
- Draft PR 614 on fix/flex-complete-20261126. Preparation document plus code/test commits 7f8e5a4b429d22eb9494f19519f96682ab8c47e1 and ceb4b710b3dec08fa58dbe71d2c6486672390f92. No payment/auth logic change.
- At code commit ceb4b710, all six source/deployment module blob hashes match: control_plane fb51a812515cd6f5a1b4360010f980e001181a7e; foundation b9956452196fed398fa5492cbc9662f44863f819; partner_portal a2872b21e6341bd26a0da84df2784de31e91db50; onboarding c46b967b9ed93c24ee8e79bdb312144d7e63965e; catalog_admin 67f934518f5ae6b2efcb9c7ffb041035d24ef277; finance_simulation a3b0737a22d70d21e1618571e2bd004fbe9a1dfa.
 
## FLEX PR inventory (open title search; 19 results)
Compared each old PR HEAD to integration SHA using GitHub compare API.
- Ancestors (ahead=0, behind>0): #574, #576, #577, #578, #579, #580, #581, #582, #583, #584, #585, #586, #587, #591 (14). Their history is included, not a guarantee that every old behavior is still correct.
- #597 identical (ahead=0, behind=0).
- #575 (ahead 2, behind 400): two changed files; NOINHERIT runtime guard and CI role tests' added lines present in integration.
- #588 (ahead 2, behind 192): 11 changed files; source comparison found password mode, role and tests present or evolved. Old session/UI snippets differ from newer implementation. Do not merge stale authentication over current. Verify behavior before disposition.
- #590 (ahead 50, behind 192): 27 changed files. Old standalone recovery helper/pages, older read-only catalog path, session renewal and UX code differ. Current Better Auth recovery and server-side session binding exist, but behavioral equivalence is NOT proven. Preserve branch; finish residual source comparison and targeted recovery/read-only/visual regression checks. Do not restore an obsolete alternate recovery endpoint or change existing authorization to satisfy history.
- #614 active draft. No PRs closed or branches deleted.
 
## Current action
Stage 0 IN PROGRESS. Finish #590 review, validate new bundle/QA route tests on exact final #614 HEAD, check candidate files/scope, retain single integration branch. Stage 1 not started. Historical cloud QA was SHA 8562addd12267e9c153e13e024a8ab01e1a84c36, 21 registered migrations; no new cloud or database writes this iteration. Recheck those at Stage 1/2. Production NO-GO, freeze 0009, real payments/payouts/ENFORCE unchanged.

## 2026-11-26 — Stage 0 verification and residual legacy review
- Exact tested candidate dc9c72de15cb08886f16755bae259408ee5f80e3: 37/37 workflow runs SUCCESS, including scope/restore 45748453456, browser/catalog 45748453586, Console 45748453830 and partner 45748453614. Scope guard: 158 isolated additive FLEX files. Integrated base remains 128ba9e3 (42/42).
- Prior red Console/Browser/migration checks corrected in dcde564, e35066a and dc9c72d. Migration runner validates 31 ledger records (30 APPLIED, 0009 frozen), 0 pending on repeat, disposable restore PASS. This is NOT acceptance of active Neon.
- #588 old head c849fab and #590 old head 5de823e retained. Compared against common ancestor b0f99f3 and tested candidate. Current enrollment already short-circuits password-mode success; current identity binds commercial cookies to exact verified Better Auth session token, not merely subject. Current recovery uses canonical Better Auth with revocation, rather than old custom recovery route. Logo retained; legacy CSS differs and full UX equivalence remains for review. Legacy administrative catalog GET with write flag off is not equivalent to current explicit catalog-draft gate; do not restore alternate router or weaken grants blindly. Core read-only /v1/catalog exists. Residual catalog/UX behavior needs verification before disposition; neither old PR is closed.
- New regression test commit d46f286118af16130ae0e7e631fd01d841f01477 extends first-login-postgres.mjs: real password sessions, distinct session tokens, stub-only mail, recovery link, invalid/short/replayed token handling, old sessions revoked and new password accepted. NOT RUN at time of commit; CI pending. No real email/cloud/database operation.
- Required branch-protection list could not be independently fetched: available GitHub connector does not expose that read endpoint; SentinelX gh CLI reports no authentication (exit 4). Combined legacy status list empty; not evidence of absence of required checks. Do not bypass merge protection.
- Stage 0 IN PROGRESS: confirm final candidate CI, finish residual legacy behavior review and native merge requirements before merge to qa/flex-pilot-20261124. Do not change main or current cloud QA. Production NO-GO.

## 2026-11-26 — residual legacy preservation (Stage 0)
- Candidate a875e5f2bf983debf22fbc43e8cfed612c54025f: all 6 FLEX workflows PASS; 36/37 overall, only AK BERMET browser job 139681581215 failed on disconnected-provider mapping persistence. Retried failed job via GitHub on the same SHA; no other-project files edited.
- Console run 45751953090 proves canonical password reset, single-use token, session revocation and new bound login with stub mail; 32/32 security tests (twice). Recovery remains on canonical Better Auth, not legacy alternate endpoints. Enrollment already returns to Console before TOTP for password-only login. Current CSS retains approved design, responsive media queries, focus indicators, 44px controls, logo and theme; legacy CSS is not blindly copied. Full role/theme/locale matrix remains Stage 8.
- Found a real #590 residual: admin catalog, version history and configuration draft history disappeared when edit mode was off. Commit 1bcfa4a9a3b75658f3f97b8697456ae2f3d00c6d restores only those three GET routes in isolated QA using existing flex_platform_admin_reader (no writer membership required). Console routes to core API when edit mode is off; editing remains explicitly gated. No migrations, live QA changes or new write permissions.
- Added regression tests for restored read-only routing, catalog/price history UI, no edit buttons, preview-only password exception and reader role; canonical recovery RU/KG/EN and invite return. Candidate tests pending; no merge or cloud acceptance yet.
- #588/#590 old heads remain intact. Old code not blindly merged. Stage 0 remains open pending final CI and native merge acceptance.
