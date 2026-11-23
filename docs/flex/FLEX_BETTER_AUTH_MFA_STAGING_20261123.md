# MARINA FLEX: Better Auth + TOTP staging (23 Nov 2026)
**Status: DISABLED, NO-GO for user login.**

- Existing Neon database `flex_qa` now contains empty, private schema
  `flex_auth`, without touching `flex_private` business tables.
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
1. Generate and review the actual Better Auth **1.7.27** migration with
   TOTP and rate-limiter plugin. Apply with an isolated migration owner,
   then verify auth tables all live in `flex_auth` and no PUBLIC grants.
   Runtime role is NOT a migration owner. Independent restore required.
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
