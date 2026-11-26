# MARINA SMART FLEX — 2026-11-26 Stage 0 factual report

Owner roadmap edition 1.0, Stage 0 only. This is an execution record, not a new roadmap.

## Evidence
- Integration base `128ba9e3d88e1a04d21d566a0e230bbfd9a1d07c`: 42/42 workflows SUCCESS.
- Prior candidate `dc9c72de15cb08886f16755bae259408ee5f80e3`: 37/37 SUCCESS; scope/restore 45748453456; catalog/browser 45748453586; Console 45748453830.
- `a875e5f2bf983debf22fbc43e8cfed612c54025f`: six FLEX workflows SUCCESS, overall 36/37, AK BERMET failure unrelated to FLEX scope. Retry requested on unchanged SHA. Console 45751953090 confirms password recovery, one-time token, prior sessions revoked, new login (stub mail).
- Reviewed legacy #588 (c849fab), #590 (5de823e), preserving old heads. Current auth uses exact Better Auth token binding, current reset uses canonical Better Auth with session revocation; do not restore alternate custom recovery endpoint. Current logo/theme/responsive controls retained, full UX acceptance remains Stage 8.
- Restored read-only admin catalogue, price versions and configuration draft history in isolated QA at `1bcfa4a9a3b75658f3f97b8697456ae2f3d00c6d`. Reader-only role, existing route guards, no writes when draft flag disabled. Added focused UI and authorization regression tests. Final SHA CI not yet accepted.

## Not done
PR #614 remains unmerged; final candidate CI and native merge protection must pass. Then verify merged integration SHA. No live Neon QA or Vercel changes, no payments, payouts, ENFORCE or PMS changes. Production NO-GO.

## 2026-11-26 — Stage 0/1 accepted; Stage 2 preparation
- PR #614 merged at `7f6055ddbb0047d84d7642530e42991a050840b0`; 42/42 workflows SUCCESS, matching deployment modules, FLEX-only scope. Stage 0 ACCEPTED.
- Stage 1 ACCEPTED: 25/25 active registry blobs match; 0009 frozen; 46/46 live commercial tables FORCE RLS. Independent archive restore from verified backup branch br-crimson-frost-bajgmcdf on Ubuntu PostgreSQL 16.15: SHA256 05244576a8645078ba0c55218795b7ae50604c5df871e3cc73ca55e41ec279c6, 52/52 data digests, 7/8 raw metadata categories, sole raw ACL difference equivalent owner default; normalized ACLs and 594 effective privileges match. Exact 21-row rehearsal applied 0022–0025 then 0026–0031, repeat pending 0, 31 records, 30 applied, zero real payments. Integrated CLI/restore run 45756314282; owner isolation job 139695644728. Evidence PR #614 comments 7183379783 and 7183470973.
- Stage 2 code preparation: customer acceptance now respects the existing verified password login only in FLEX QA/Vercel Preview with catalog drafts enabled. Signed token verification, live membership, hotel scope, non-inherited writer role, digest/acknowledgement checks and production MFA boundary unchanged. Source/deployment mirrors updated together. Existing CI required; no extra tests added. No active QA migration/deployment authorization inferred. Stage 2 remains IN PROGRESS; owner approval must identify accepted final SHA and Neon QA target. Production NO-GO.
