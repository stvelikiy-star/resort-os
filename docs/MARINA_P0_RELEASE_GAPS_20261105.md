# MARINA SMART — P0 gap register, 2026-11-05

## Verified baseline

Draft PR #367 at SHA `e63b11b1a4f78806c1e5f1dce4f238317ce76ef2`: **100/100 GitHub Actions SUCCESS**. These are CI results, not an external staging or commercial deployment acceptance. A later commit requires its own CI.

This follow-up does not touch frozen RC3 source, migration SQL, DEMO, `apps/mobile`, production database or Ubuntu.

## Source-confirmed blocking gaps

| Surface | Accepted in shared preview | Commercial launch blocker | Evidence |
| --- | --- | --- | --- |
| Auth / roles | 12 roles authenticate in two disposable hotels; owner manages six staff roles | External production-session acceptance and broader staff workspaces missing | `scripts/marina_shared_role_auth_ci.py`, `services/api/app/staff_control.py` |
| RECEPTION | Booking read, check-in/out, tasks | **Cannot create a PMS booking:** canonical create API grants OWNER/MANAGER/AGENT; shared Admin renders booking form only for OWNER/MANAGER | `services/api/app/pms_reservation_create.py`, `apps/admin/app/shared-auth-preview/page.tsx` |
| COOK / WAITER | Accounts exist and authenticate | No accepted shared dining endpoints or working shared staff UI; Staff gateway admits only MAID/TECHNICIAN in shared mode | `services/api/app/shared_auth_preview.py`, `apps/staff/components/StaffRoleGateway.tsx` |
| Other roles | Legacy role enum retained | STORE_STAFF, DINING_STAFF, CONTENT_MANAGER, BEACH_PARTNER lack accepted shared operational cabinets | `docs/MARINA_SHARED_AUTH_MOBILE_CONTRACT_20261104.md` |
| PMS and money | Browser+real PostgreSQL tests cover two-property booking/HOLD/recorded payments/stays | External staging, bank reconciliation and refund settlement **not proven**; manual payments are not acquiring | `scripts/marina_shared_live_browser.mjs`, `docs/MARINA_SHARED_FINANCE_AUDIT_RC_20261104.md` |
| WhatsApp / AI | RC7 webhook and RC8 human outbound synthetic contract PASS | Real two-instance provider delivery, knowledge isolation, reconnect and handoff not verified | `services/api/app/shared_green_rc7.py`, `services/api/app/shared_green_rc8.py` |
| Production | Isolated Compose/staging instructions, PostgreSQL restore rehearsal | Customer-target TLS, backup/restore, rollback, monitoring and production smoke not accepted | `docs/MARINA_SHARED_HTTPS_STAGING.md` |

## Next P0 actions and acceptance

1. Preserve immutable RC3 and migration checksums. Do not bypass source lock; any necessary change to its frozen files requires an explicit separately reviewed versioned rebaseline.
2. Add RECEPTION **core-rate-only** booking to the canonical API and shared Admin, with no manager price override; verify 201/403/404/409 and hotel isolation using real PostgreSQL.
3. Add shared COOK and WAITER role-limited dining workspaces only after two-hotel browser→API→DB tests. Determine separately which other roles must ship at launch.
4. Accept real guest QR requests, live provider WhatsApp receipts and MARINA AI human handoff on isolated external HTTPS staging.
5. Prove third-hotel onboarding, restore/rollback and monitored host before commercial GO. Require required CI PASS on one final SHA.

## Narrow improvements in this change

- Staff browser shared login now requires eight password characters, matching canonical server validation, while legacy single-property six-character UI behavior is unchanged. Chromium HTTPS staff tests enforce this contract.
- Existing booking form already discards its quote on guest-name/phone edits. The Chromium HTTPS PMS test now checks this positive behavior, including renewed quote before the booking commit. No server pricing logic is modified.
