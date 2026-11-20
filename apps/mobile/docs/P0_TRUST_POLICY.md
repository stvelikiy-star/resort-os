# P0 hotel origin trust policy — mobile-only (03.11.2026)

The old QR connection flow accepted any syntactically valid HTTPS domain, a phishing risk.

## New fail-closed gate

Only hotel API origins explicitly compiled into the independently distributed app build are trusted. Set `EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS` at build time to a comma-separated list of **exact canonical HTTPS origin+prefix** addresses reviewed by the operator. Example for tests: `https://hotel.example/core` (not a real hotel). If unset, **all LIVE connections are denied**; synthetic DEMO remains available. There is intentionally no bundled `ms.go.kg` or user-supplied hotel host in this commit because production API host ownership was not independently verified.

The gate runs on QR scan, manual addition, saved-connection restore, hotel selection and immediately before sending a password; the live module accessor also declines untrusted connections. Accepting a signed QR in the future requires a separately approved public verification key anchored in the distributed app. A remote self-issued `/.well-known` file is **not** an identity proof.

The compiled public allowlist is NOT secret. It is pinned only by the integrity of the signed application; use independent domain ownership / release-signing verification before adding any host. No host suffix matching, wildcard, untrusted redirect or HTTP fallback. Browser previews and unsigned development builds should not be treated as security attestations.

## Remaining release blockers

1. Native server auth with short-lived access, rotating refresh and revocable device registry — backend contract required; cookie mode remains temporary.
2. Native signed application distribution and device-level acceptance, including lost/stolen device and re-employment.
3. An authoritative MARINA-operated discovery/registry service for flexible property onboarding, with signature/key rotation.
4. Real cross-tenant auth and permissions E2E against isolated staging hotels.
5. Existing API transport must reject cross-host redirects (addressed separately in HTTP transport refactor).

**No server changes, no database migrations, no platform deployment in this PR.**
