# Public MARINA demo on the existing Ubuntu

This deploys the actual PMS with its own `MARINA_DEMO` database and Docker
volume. It does not alter `marina-hotel01`, ASKA TASH, BANZAI or DNS.

## Requirements

Use the accepted release checkout with Docker Compose and Python 3. Three real
DNS names must point to the Ubuntu's public ingress. Its inbound TCP 80/443 must
be reachable for Caddy automatic HTTPS. A private Tailscale address alone does
not provide public ingress. Do not replace the marketing site's DNS record.

Suggested names to configure in DNS, **not yet provisioned by this package**:
`demo.ms.go.kg` (Admin), `staff-demo.ms.go.kg` (Staff),
`guest-demo.ms.go.kg` (Guest). Use the owner's actual TLS contact email.
Guests open the `/g/<token>` link issued for a synthetic stay. The guest host's
root redirects to the demo Admin instead of showing the legacy hotel homepage.

If a proxy already owns 80/443, the script stops. Add the demo hosts to that
existing proxy rather than stopping it or starting competing Caddy instances.
`deploy/marina/demo.Caddyfile` shows the required routes; the existing proxy
must join the demo network or proxy to the existing loopback ports.

## Start

```bash
bash scripts/marina_demo_public_start.sh \
  demo.ms.go.kg staff-demo.ms.go.kg guest-demo.ms.go.kg OWNER_TLS_EMAIL
```

Replace `OWNER_TLS_EMAIL` before running. The script preserves existing demo
credentials and reservations, refuses an orphaned demo volume without its
credentials, builds serially, and enables Secure cookies and explicit origins.
No provider credentials are configured; real payments and external AI remain
disabled. Credentials are stored in `.marina-demo.env` with mode 0600 and never
printed by this script. Existing local demo credentials must use the generated
URL-safe format; unsupported values cause a stop without password rotation.

The success marker requires valid public HTTPS for all three UIs, the correct
property, actual owner login, Secure/HttpOnly cookie and authenticated `/me`.
If DNS/ACME is still propagating, a failed final verification is not publication
success; inspect Caddy logs, resolve DNS/ingress, and rerun with the same inputs.

Only give clients the link after testing it from another network. Clearly tell
them that all rooms, bookings and contacts are synthetic. Supply separate
personal demo access through Staff management; never reuse real hotel accounts.
The package does not claim automated cleanup, per-visitor sandboxing, backup
acceptance, live AI, OTA or WhatsApp connectivity.

## Stop public ingress without deleting demo data

```bash
docker compose --env-file .marina-demo.env \
  -f compose.marina-demo.yaml -f compose.marina-demo-public.yaml stop caddy
```

Never use `down -v` on this demo to deploy an update. The original local-only
start script does not include the HTTPS overlay; use the public script for
subsequent public-demo updates.
