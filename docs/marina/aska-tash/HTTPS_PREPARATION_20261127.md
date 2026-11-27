# ASKA TASH permanent HTTPS — preparation only

Scope: existing ASKA_TASH pilot; no other MARINA SMART property, FLEX, KÖL, DNS zone, customer database or running containers may be changed by this preparation. Live release observed 7c23fbd479dcc6f8c90b1fa5fbd05688315e5f93. The source baseline for this documentation-only draft is f4deb91ffc7b837db557bcf1282f48fbba02bdb1. This is not an authorization to deploy.

## Evidence, 2026-11-27

cloudflared 2026.11.2 (built 2026-11-23T13:03Z) is installed. Local readiness: guest /guest, /g/sample and /core/health/ready; admin / and /core/api/v1/auth/mode; staff /, /core/api/v1/auth/mode, /kitchen and /waiter; API /health/ready and /api/v1/auth/mode all HTTP 200 (11 routes). Host ingress is loopback only for the four origins. No additional inbound TCP 80/443 required for Cloudflare Tunnel.

Validated the exact example YAML in a disposable temporary directory using cloudflared tunnel --config <file> ingress validate, then ingress rule for each of four .invalid hostnames and an unmatched hostname. Six commands exit 0; expected four local upstreams plus final http_status:404 matched. No live tunnel configuration, public DNS or service changes made. The .invalid names and UUID are placeholders, not operational DNS or tunnel credentials.

## Proposed implementation, pending specific owner authorization

1. Obtain the actual four hostname names approved specifically for ASKA_TASH and confirm authoritative DNS zone and existing records. Do not take over app.ms.go.kg, staff.ms.go.kg, kol.on.kg, FLEX or another hotel's hostname.
2. Use the existing Cloudflare plan, if the approved zone supports a named tunnel. Create a separate named ASKA_TASH tunnel and connector only after approval; preserve current tunnel and other services. The connector can run on Ubuntu with outbound access. Keep tunnel credentials in protected server-side storage. Never put them in Git or chat.
3. Replace placeholders in a private copy of the example configuration. Use the named tunnel's actual ID and credentials configuration. Validate ingress and record DNS rollback before applying. Configure the four explicit public hostnames; no wildcard forwarding and no public Postgres.
4. Review exact guest base URL, API CORS origins, cookie scope, Secure cookies, reverse proxy host handling, rate limiting and same-origin WebSocket policy before external acceptance. Do not broaden trusted proxy or allowed origins, bypass auth, enable payments or expose admin data to guests. Existing public site and mobile endpoints require functional checks; routing alone is insufficient.
5. Verify external TLS/certificate hostname, guest QR URLs, API readiness, Admin and Staff sign-in with approved test identities, WSS, mobile access, no-payment route negatives, and error monitoring. Record hostnames, exact SHA, timestamp and receipts without secrets. Preserve existing access until acceptance; no automatic cutover.
6. If any acceptance fails, remove only newly authorized ASKA_TASH ingress/DNS using the recorded rollback; do not disturb the previous deployment. Require separately verified offsite backup and explicit owner GO for production cutover.

Blockers: ASKA_TASH domain names/zone not confirmed; no named tunnel or external HTTPS receipt established in this turn; local readiness does not prove authorized business flows. Keep permanent HTTPS gate RED pending actual external verification.
