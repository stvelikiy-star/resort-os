# Cookie-session pre-login revocation — interim mobile security policy

The existing MARINA backend uses a shared origin cookie. Cookie jars survive
application restarts and logout queue storage can fail; therefore a brand-new
login must **never** assume the previous device cookie has gone away.

In LIVE mode, before submitting employee credentials, the mobile client:
1. Verifies the HTTPS hotel origin against the signed-build allowlist.
2. Tries replaying pending server-side revocations.
3. Blocks login if an unacknowledged prior logout for this host remains.
4. **Always calls verified backend `POST /api/v1/auth/logout`**, even with an
   apparently empty pending queue, to revoke any preexisting OS-held cookie.
5. Submits credentials only after server ACK and rechecks the login attempt,
   user identity and hotel against `GET /auth/me`.

The established backend returns HTTP 204 for an anonymous logout. If step 4
cannot be confirmed (offline, timeout, service unavailable), login is blocked
without transmitting credentials; the UI shows a specific pending-logout
message. This is intentional fail-closed behavior. DEMO mode is separate.

This mitigates stale cookie reuse but is **not** refresh-token rotation,
real device revocation or a guarantee that other devices/cookies were revoked.
Backend contract request: #295. Real Android/iOS lost-device testing remains
required. Server/database/deployed demo are untouched.
