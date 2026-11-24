# MARINA FLEX: Better Auth + TOTP staging (23 Nov 2026)
**Status: DISABLED, NO-GO for user login.**

- Existing Neon database `flex_qa` contains private schema `flex_auth`
  with exactly **six** Better Auth **1.7.27** tables:
  `user`, `session`, `account`, `verification`, `twoFactor`,
  `rateLimit`. SQL generated from the canonical auth configuration by
  GitHub Console CI using disposable PostgreSQL 16, NOT a guessed schema.
  Applied first to existing isolated restored branch
  `br-jolly-wave-ba4j30om`, then transactionally to default `qa`
  `br-spring-rice-bak1xu5l`. **PASS** for table creation, foreign keys,
  indexes, and 0 PUBLIC table grants. There are 0 FLEX membership records
  and 0 confirmed payments. No PMS files or `flex_private` tables modified.
- New **role**, not new project/database: `flex_auth_runtime`, no
  SUPERUSER/BYPASSRLS/CREATEROLE/CREATEDB and no privileges on hotel or
  payment tables. Its restricted connection string is stored as a Vercel
  **Preview sensitive** environment variable `FLEX_AUTH_DATABASE_URL`.
- Vercel Preview `FLEX_AUTH_ENABLED=false`; new identity routes return
  503 and NEVER instantiate Better Auth or connect to the database.
- Staging code in existing Console loads Better Auth **1.7.27** + TOTP
  only when audited schema, exact HTTPS origin, a strong app secret, and
  explicit QA flags are configured. No public signup is allowed.
- A Better Auth cookie is **not** a platform JWT. No privileged role
  is minted, no session counts as confirmed MFA, and write routes remain
  OFF. Existing OIDC/BFF is unchanged.

## Next release gates, strictly sequential
1. **DONE — schema install:** Generated 11 DDL statements from the pinned
   Better Auth **1.7.27** + TOTP + rate-limit configuration in GitHub CI;
   reviewed and installed six tables in the restored QA branch and default
   QA branch, without any PUBLIC grants or PMS/business writes. The runtime
   role does not own schema. An additional pre-migration Neon snapshot was
   blocked by Free-plan snapshot quota. Existing separate restored branch
   provided a non-destructive verification point, **not** an external R2
   backup. Independent off-site backup remains a separate release gate.
2. Set independent 256-bit `BETTER_AUTH_SECRET` and an exact stable HTTPS
   `BETTER_AUTH_URL`, Preview sensitive only. Set
   `FLEX_AUTH_SCHEMA_READY=true` only after verified migration.
3. Verify password login, email proofing, TOTP enrollment and challenge,
   recovery controls, expiration/revocation, rate limiting and disabled
   signup with real sessions.
4. Implement and audit the **server-attested** MFA-to-EdDSA access token
   bridge accepted by Python FLEX API. The stable OAuth provider does
   not by itself guarantee `amr:["mfa"]`. Never trust browser claims,
   mere `twoFactorEnabled`, or `trustDevice` as MFA proof.
5. Only then create a verified SUPER_ADMIN member and enable registration
   and catalog draft writers after live end-to-end isolation checks.

NO PMS changes, NO live payments or banking, NO new external platform.

## Verified database facts, 2026-11-23

- Auth table count: **6**; PUBLIC table grants: **0**.
- `flex_auth_runtime` reads/writes only auth schema; has **no** USAGE on `flex_private`.
- `flex_platform_memberships` = 0, confirmed payment rows = 0.
- These are DB migration facts, **not** successful TOTP sign-in or signed
  platform JWT acceptance.
- FLEX writer and payment flags must remain OFF during identity QA.
