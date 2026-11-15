# MARINA SMART Future Luxury 2.0 — single-SHA Draft integration candidate

**Status: DRAFT / NO-GO. No production cutover permission.**

## Exact accepted source inputs
- Web OWNER/PMS + Staff/Guest visual source: PR #503, `1ab7e68a535e7ac03740ae9ad160682fa57669fe`, 32/32 CI PASS.
- Guest Core integration: PR #507, `7409cd854d0309a71be9d3a0f7decf8b7783b20f`, 5/5 CI PASS.
- Mobile booking card, role and visual source: PR #532, `fec8efef5a0c6afaecdd4eab965de65d9004bb5a` (candidate input; verify exact SHA CI separately).
- Public AI forwarded-header security regression: PR #523, `37eb9b74e3fc6b79fb8f302c06367f25f6243347`, 32/32 CI PASS.

This is a test-only integration tree of distinct reviewed paths, **based on the Web C12 approved source** to preserve public-marketing freeze boundaries. No existing code features were removed or redesigned; no frozen RC2/RC3 release manifest was altered.

## Release blockers
1. Exact combined-head GitHub CI must PASS. Historical individual CI PASS is not interchangeable with combined SHA evidence.
2. The historical RC3 HOLD source-lock remains a separate mandatory blocker for the HOLD promotion track. Mobile `pmsHolds:false` must stay false; HOLD activation is NOT authorized.
3. Physical Android E2E (OWNER/RECEPTION real sign-in, stay operations, network loss, tenant isolation and server revocation) NOT VERIFIED.
4. GitHub `main` is not protected by branch protection/rulesets as seen by available API; administrator review and required statuses are pending.
5. Full visual comparison against original approved screens (RU/KG/EN, Dark/Light, all roles and edge states) is NOT COMPLETE.
6. Real live HTTPS / Ubuntu / ASKA TASH / production operations NOT PERFORMED.

**Commercial verdict: NO-GO** until all blocking gates and external device verification are recorded.
