# MARINA SMART — canonical shared hotel authentication contract (P0, 2026-11-04)

**Contract ID:** `marina-shared-auth-v1` — isolated shared-auth **staging** only, not production deployment, not DEMO or single-property hotel01. Server source base: `cb04266ab5d67e5358f0e78c3635b02fb3d47837`, role-ceiling Draft branch `fix/marina-shared-auth-role-ceilings-20261104`. Mobile source reference when drafted: `bd75fdb5b2dcec17d3aa8458b34d31a58b765254`, PR #315. Final accepted server SHA must be taken from the PR head **after** all required CI PASS.

## 1. Select hotel and sign in

The shared runtime hosts multiple unrelated hotel owners. Login **always** requires three separate user-facing inputs: the issued organization code (`tenant_code`), the issued hotel code (`property_code`) and the staff credentials. There is **no public organization enumeration or trusted free-form property header**. Codes are selectors, **never authentication**; the server binds membership to the database.

```http
POST /api/v1/auth/login
Content-Type: application/json

{"tenant_code":"tenant_a","property_code":"HOTEL_A",
 "username":"reception","password":"<user-entered secret>"}
```

- `username`: 2–80 chars, trimmed/lowercased server-side. `password`: 8–256 chars in shared mode.
- `tenant_code` and `property_code`: 3–80 characters, pattern `^[A-Za-z0-9][A-Za-z0-9_-]*$`. They are **required in shared mode** and rejected in legacy property-pinned mode. The server must reject an absent/mismatching selector with 401.
- No `tenant_id`, `property_id`, `role` or `module_permissions` input is allowed as an authority-bearing field. No mobile-supplied `X-Tenant-Id`/`X-Property-Id`/`X-Role` header grants access.
- `POST /auth/login` and `GET /auth/me` return the SAME identity shape:

```json
{"id":"<staff uuid>","username":"reception","display_name":"Reception",
 "role":"RECEPTION","property_code":"HOTEL_A",
 "property_id":"<server database uuid>","tenant_id":"<server database uuid>",
 "module_permissions":["DINING","GROUPS","PMS","RESERVATIONS","ROOM_QR","SERVICES","WHATSAPP"],
 "module_permissions_custom":false}
```

The above is an **illustrative shape**, not data copied from a real hotel. The actual fields/values must be read from the API. Only twelve server roles exist in the current enum: `OWNER`, `MANAGER`, `RECEPTION`, `AGENT`, `MAID`, `TECHNICIAN`, `STORE_STAFF`, `DINING_STAFF`, `COOK`, `WAITER`, `CONTENT_MANAGER`, `BEACH_PARTNER`. A role's login success does NOT imply that a shared operational workspace exists.

## 2. Session and revocation

- Auth cookie name `resort_session`; **HttpOnly**, `SameSite=Lax`, path `/`, scoped to the connected HTTPS origin/domain. The server controls `Secure`/cookie domain; **production must use HTTPS and Secure cookies**. No raw bearer or refresh-token API is asserted by this contract.
- Client uses `credentials: include`, `redirect: error`, and verifies `GET /api/v1/auth/me` immediately after login. Missing/mismatching identity is failure, never a successful login.
- In shared mode the server-issued `ms1.<tenant_uuid>.<property_uuid>.<random>` cookie is stored as a **SHA-256 token hash** in `auth_sessions`. The clear token is not persisted. On every request the server revalidates the current staff record, active tenant/property relationship, user activation, token expiry/revocation and token-bound tenant/property IDs. Tenant/provider selectors on another hotel never switch an existing session.
- `POST /api/v1/auth/logout` returns 204, revokes the session in PostgreSQL and deletes the cookie. Mobile must erase UI state immediately; it must not assume local cookie removal alone revoked the server session.
- An owner-driven role/password/module/activation change through the canonical staff API revokes existing affected sessions. Next request with the prior cookie must return **401** and the client must clear the prior identity. A fresh login obtains current grants.
- 401: login required/stale session; 403: active session but operation not allowed; 404 on cross-property records: record must not be discoverable; 503 in shared preview: route **not yet accepted/deployed**, not a mobile permission prompt. Never auto-retry mutations of unknown outcome.

## 3. Role and module authorization

The **shared multi-hotel** environment uses two server-enforced checks:
1. The role must be included in the endpoint's allowed roles. A checkbox alone cannot grant `OWNER`/`MANAGER` powers to `RECEPTION`, `MAID`, `TECHNICIAN`, `COOK`, etc.
2. Explicit module permissions can only **narrow** what the role already permits. `OWNER` is the hotel-level owner and retains its hotel-wide rights; the manager can be narrowed by its owner.

Effective shared role ceilings:
- `OWNER`: hotel-local owner capabilities.
- `MANAGER`: owner-granted modules, only within its manager role.
- `RECEPTION`: `PMS`, `RESERVATIONS`, `SERVICES`, `DINING`, `ROOM_QR`, `GROUPS`, `WHATSAPP` (some sections still staging-closed).
- `AGENT`: `PMS` only, **and** the staff account must be linked to an ACTIVE, hotel-local `booking_agents` record. The CI fixture intentionally has no booking-agent membership, so a logged-in AGENT receives **403** for the grid until onboarding/linkage is explicitly accepted.
- `MAID`: `OPS`/HOUSEKEEPING only. `TECHNICIAN`: `OPS`/MAINTENANCE only.
- `COOK`, `WAITER`: `DINING` only (**shared cooking/dining endpoints currently closed**).
- `STORE_STAFF`, `DINING_STAFF`, `CONTENT_MANAGER`, `BEACH_PARTNER`: the enum records still authenticate but have no accepted shared preview modules. Never show unimplemented features.

A module in the response is **not proof of a deployed route**. Mobile must bind its UI to **role + permission + confirmed environment capabilities**, never to a module checkbox alone. Current shared Admin is deliberately limited to dashboard, grid, reservations, staff overview/owner management, and task operations for approved roles. Other routes return 503 in staging.

## 4. Required mobile implementation follow-up (Claude Code only)

- In `apps/mobile`, add trusted organization/hotel selection to LIVE login without changing backend auth. Send both codes and verify login plus `/me` response and stored hotel identity match. Store only the minimal issued selector metadata; do not cache a raw session token in insecure storage. Do not silently reuse a different hotel's cookie.
- Keep one canonical server business layer for reservations/HOLD/tasks/finance and hotel-local authorization; do not implement second PMS. Mobile PR #315's `pmsHolds:false` contradicts the tested server HOLD contract, and its `Hold` shape needs server snake_case mapping. Separate mobile-only work item.
- Do not infer availability of shared WhatsApp/AI/dining/guest QR APIs from files alone; external staging and actual-device session persistence/revocation remain **NOT TESTED**.
- Do not touch server release, migrate or merge mobile PRs automatically.

## 5. Verified / not yet verified

Validation requires 24 role logins (all 12 roles × 2 independent properties) in **canonical FastAPI + disposable PostgreSQL** with positive/negative endpoint checks, tenant header spoofing, identical usernames across hotels, module grant ceiling, owner-driven revocation and independent hotel preservation. The existing separate two-hotel Chromium→Next→API→PG acceptance continues to verify PMS/tasks.

**Evidence is accepted only at one final PR SHA with required CI PASS**. No claim is made about production HTTPS native cookies, OAuth/device tokens, external hotel onboarding, mobile LIVE E2E or target database restore. All deployments, mergers and working customer databases remain NO-GO.
