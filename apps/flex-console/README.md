# MARINA SMART FLEX — isolated commercial console (read-only QA)

This app implements the **existing Future Luxury 2.0** visual language (navy/cyan/champagne) with role-bound views. The exact six-screen approved interactive reference remains at `docs/flex/ui/MARINA_FLEX_Interactive_Prototype.html` and is NOT served on the authenticated origin.

## What's implemented

- SUPER_ADMIN: verified hotel registry and hotel detail (subscription + invoice reads), published SKU catalog, synthetic partner liability overview.
- HOTEL_OWNER: only backend-authorized hotel subscription/invoices and published catalog.
- SALES_AGENT / INVESTOR: only own day/week/month QA earnings (MFA enforced by FLEX API for investors).
- Responsive desktop/mobile, RU/KG/EN, dark/light. Loading, empty, 401/403 and offline states.
- Server-side BFF, **strict allowlisted GET proxy plus one explicitly gated PENDING-only QA registration route**, encrypted HttpOnly same-site cookies, OIDC authorization-code with PKCE, JWT/JWKS verification, issuer/audience/nonce validation. The browser never receives raw bearer tokens.
- No role picker in live mode; role comes from `GET /v1/me` validated by backend. No writable bank, subscription, entitlement or payout routes.

## Run offline for UI smoke

```sh
cd apps/flex-console
node --version  # v22+
npm test
npm start
# http://127.0.0.1:3407
```

Without an issuer and live backend, the UI accurately says **QA not configured**. It does NOT fall back to invented balances, demo hotel names or browser-supplied roles. The six-screen approved design reference can be inspected as a standalone HTML file; it is deliberately **not exposed by the authenticated HTTP server**.

## Buttons and safe actions now wired

- Hotel search and status filters, hotel drill-down, subscription and invoices: request live FLEX API (not mock data).
- Refresh buttons fetch current backend state again.
- CSV exports for hotel registry, SKU pricing, invoice lists, agent/investor own earnings and admin QA aggregates. Export is explicit, not cached in browser localStorage.
- SUPER_ADMIN hotel registration: real POST `/api/actions/hotels` with same-origin protection, encrypted session-bound CSRF token, validated KGS-only request and `Idempotency-Key`; it calls the EXISTING separate FLEX onboarding API, creating only `PENDING` hotel with `billable=false`.
- Day/week/month earnings filter is backed by the existing QA partner statement API. Locale and appearance controls work locally.
- New offline test simulates OIDC + signed JWT/JWKS, registration, rejected cross-site POST/CSRF, idempotent replay, wrong currency and forbidden payout writes.
- Payout, real payment, invoicing, entitlement enforcement and subscription mutation remain deliberately unavailable. Never fake a successful live financial action.

**Enable test hotel registration only in a dedicated approved QA service:**

```sh
FLEX_ENVIRONMENT=qa
FLEX_ENABLE_QA_ONBOARDING=true
FLEX_ONBOARDING_API_ORIGIN=https://<qa-onboarding-private-origin>
```

All 3 variables are required in addition to the platform issuer and API configuration. Without them the button stays disabled. The backend independently requires database-verified SUPER_ADMIN with MFA. This DOES NOT create a live hotel in operational MARINA SMART.

## P0: Trusted hotel connection (QA only, no payments)

SUPER_ADMIN hotel details now offer **Link to MARINA SMART**:

1. Enter a registered `deployment_id` and the corresponding hotel `property_external_id` only in an **isolated, authorized QA environment**.
2. The UI calls `POST /api/actions/hotels/<uuid>/challenge`. The backend checks `PENDING`, MFA, trusted deployment and writes a 10-minute challenge. Nothing is linked yet.
3. Deliver the displayed exact `signed_message` to the **registered trusted MARINA SMART deployment signer**. The browser or FLEX console **never signs it and never stores a private key**.
4. Paste only the approved Base64 signature. `POST /api/actions/challenges/<challenge_id>/confirm` checks the signature against the pre-registered public key, expiry, one-time use and ownership uniqueness.
5. On verification the page says **VERIFIED; subscription not activated**. No payments, invoices, subscriptions, feature flags or operational PMS content are changed.

To enable on approved isolated QA only:

```sh
FLEX_ENVIRONMENT=qa
FLEX_ENABLE_QA_ONBOARDING=true
FLEX_ENABLE_QA_LINKING=true
FLEX_ONBOARDING_API_ORIGIN=https://<isolated-onboarding-private-origin>
```

All four values are necessary; no toggle or fake signature is available from browser UI. Without an approved signer the confirmation cannot succeed. For every request the BFF requires a same-origin browser, encrypted session, matching CSRF and strict schema. The backend independently verifies signed Ed25519 proof and server-authorized SUPER_ADMIN+MFA.

The synthetic E2E test generates **disposable test signing keys in memory**; they are never reused by any actual MARINA SMART deployment. Keep trusted production/PMS secrets away from this QA environment.

**Not yet implemented:** catalog publication and price-version administration, subscriptions state changes, agent/investor contract writes, or live deployment. These need dedicated safe transactional APIs, never imitation HTML mutations.

## Separate managed QA environment only

Set these server-only environment variables (never commit values):

```sh
FLEX_PUBLIC_ORIGIN=https://<qa-console-host>
FLEX_API_ORIGIN=https://<qa-control-plane-private-origin>
FLEX_PARTNER_API_ORIGIN=https://<qa-partner-portal-private-origin>
FLEX_OIDC_ISSUER=https://<dedicated-platform-issuer>
FLEX_OIDC_CLIENT_ID=<client id>
FLEX_OIDC_CLIENT_SECRET=<secret if confidential client>
FLEX_API_AUDIENCE=<exact audience accepted by backend>
FLEX_SESSION_KEY=<base64 of 32 cryptographically random bytes>
FLEX_ENVIRONMENT=qa
FLEX_ENABLE_QA_ONBOARDING=true   # only when synthetic QA hotel creation is approved
FLEX_ONBOARDING_API_ORIGIN=https://<isolated-onboarding-service>
HOST=127.0.0.1
PORT=3407
```

Register **exact** redirect URI `<FLEX_PUBLIC_ORIGIN>/api/auth/callback` with the issuer. Require MFA on all platform management users at the issuer AND keep backend role/MFA validation; access token must be JWT verifiable with the issuer's JWKS and match backend EdDSA requirements. Ensure BFF traffic to backend is private/TLS, no forwarding through a live PMS endpoint. Use an approved QA ingress/proxy before exposing this server to testers.

**Deployment NO-GO until:** independent FLEX QA DB in private schema, issuer/MFA with real users, restricted DB grants, negative two-hotel/two-agent/two-investor E2E, R2/offsite encrypted backup+restore, legal/bank approvals where required, and release governance review. Do not change historical November release checks or enable production restrictions.

**Backend currently QA-only:** see PR #575, #577, #584, #585. There is no live payment provider, fiscal confirmation, bank payout or entitlement enforcement.

## Security & status interpretation

The OIDC broker uses encrypted browser cookies; session rotation/refresh and advanced audit logging are release hardening items. Only a small allowlisted surface is proxied. MFA is checked at the backend (SUPER_ADMIN/INVESTOR). Platform OIDC identities must be provisioned separately; this project does not create users or keys. No bank data, production PMS, or other projects are touched.

The original six-screen demo intentionally contains fictitious numbers; **none** of them are considered production financial statements.
