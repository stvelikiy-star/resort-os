# MARINA SMART — P0 Guest QR multi-hotel acceptance (2026-11-04)

## Scope and hard boundary

This file is **test/release evidence**, not permission to deploy or enable Guest OS.

- Shared platform lineage: platform/staff #338 -> #339 -> #341 -> #343;
  Guest OS property-bound hardening Draft #344 (accepted CI head
  \`4577c1c6b1f8bfae54475d8cc68ea18dcc3af928\`).
- Guest QR two-hotel HTTPS implementation: Draft #346, isolated source only.
- Single shared architecture: **one** FastAPI/Next/PostgreSQL installation,
  independent Tenant/Property for unrelated hotel owners. The QR token,
  not a request header or phone username, resolves its property.
- No changes or acceptance for \`apps/mobile\`, Ubuntu host, DEMO,
  production databases, integrations or \`main\`.
- Existing \`SharedAuthPreviewBoundary\` remains untouched: Guest OS routes
  on the actual shared preview still respond **503**.
- The test-only \`scripts/marina_shared_guest_qr_ci_app.py\` composes only
  existing auth/PMS/stay/Guest OS routers, without adding new product APIs.
  It refuses startup unless the disposable localhost DB name, synthetic
  credentials, explicit staging guard and Secure-cookie checks all match.

## Independent two-hotel E2E assertions

\`MARINA Two-Hotel Guest QR HTTPS CI\` applies the unchanged Prisma migration
chain to a new PostgreSQL instance and seeds HOTEL_A / HOTEL_B (two tenants,
two owners, separate rooms and hotel-specific rates). Over real TLS
\`https://localhost:18443\`, using canonical server endpoints, it checks:

1. Owner login and /auth/me bind each tenant; forged tenant/property headers
   do not grant access to foreign QR issue/rotation.
2. Issue persistent room QR with a random one-time-display token; both URLs
   use one explicit HTTPS origin, but distinct room/tenant QR IDs and tokens.
3. Book/confirm using canonical PMS rates, check in, issue guest PIN; before
   verification the guest context returns **no guest or stay PII**.
4. Five invalid PIN attempts return 401 then 429 despite changing
   X-Forwarded-For and User-Agent; guest PIN fingerprint uses canonical
   trusted-proxy policy and cannot be reset with user-controlled headers.
5. A/B guest cookies unlock only their own stay: foreign room view returns
   generic context and foreign service reads/writes return 401.
6. Own guest task creation writes only the local Property/Room/Stay; active
   duplicate is refused, and PostgreSQL checks the property and task IDs.
7. Logout of A does not revoke B. Check-out revokes each active guest
   session. Rotation revokes only the old A room QR; B remains active.
8. No external API calls, real payment, provider interaction or customer
   data writes; disposable CI only.

**Verified evidence before the final PR branch-name correction:** dedicated
HTTPS job PASS on historical run 41826738711 and 41827583148. These are
synthetic CI outcomes, NOT external production acceptance. All checks must be
re-evaluated for the final PR head before calling the *new* candidate green.

## Shared QR origin requirement

When shared-auth preview is enabled, issuing a QR requires an explicitly
configured \`GUEST_OS_PUBLIC_BASE_URL\` with HTTPS scheme, hostname, root path
and no credentials/query/fragment. The old single-property fallback
\`https://3korony.com\` is intentionally **not** reused by unrelated hotels.
Loopback origins work only under the dedicated disposable CI confirmation.
Legacy single-property behavior is otherwise unchanged.

\`MARINA Shared Auth Preview CI\` is expected to keep its separate historical
PostgreSQL fixture working with a reserved \`.invalid\` test origin, without
opening any shared Guest OS routes. Never use the \`.invalid\` origin for real QR.

## Release blockers (NO-GO)

- Actual all-module shared preview still returns 503 for Guest OS. A
  **separately reviewed release-candidate** change to the protected
  shared-route allowlist and deployment flags is required; never bypass the
  current RC3 source lock or edit its frozen 39 migration checksums.
- The public Next \`/g/[token]\` page has not yet been browser-tested on the
  **same shared HTTPS origin and cookie jar** as the canonical API. This
  acceptance job covers the server, not a rendered guest browser UI.
- Real guest-facing service catalog, photos/storage, role handoffs, language
  correctness and accessibility must be verified against two real hotels.
- No external staging deployment, Ubuntu restore, live provider, payments or
  mobile real-device E2E is established by this synthetic harness.
- The historical **Three Crowns Full Staging Gate** is a legacy single-hotel
  site-specific CI that is intentionally scoped out for
  \`test/marina-shared-*\` branches, as declared by that workflow. Its hard-
  coded source-copy guard cannot be used to validate the current shared
  MARINA SMART / AK BERMET public site.

**Decision:** do not merge or deploy until all product-specific gates for the
one final accepted SHA pass, the public guest browser flow is tested, and
the shared module admission has independent two-hotel security approval.
