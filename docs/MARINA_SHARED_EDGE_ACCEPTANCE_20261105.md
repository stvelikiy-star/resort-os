# MARINA SMART — shared Ubuntu HTTPS edge, isolated hotel stacks

**Scope: preview-only code and static/Compose contract tests. No live Ubuntu deployment is authorized.**

## Architecture

A single Caddy `marina_edge` owns host 80/443 and routes by validated public hostname.
Each hotel has **its own** private Docker Compose project, PostgreSQL, application containers,
n8n, persistent files and secrets, with no customer-facing hotel switch.

A hotel's `customer_gateway` Caddy is connected to that hotel's private `resort`
network **and only its own** ingress network `marina_ingress_<project>`.
It is **not** published on the Ubuntu host. The shared external Caddy joins
the two (or more) separate ingress networks. Hotel A's gateway cannot resolve
or connect to B's `postgres`, `api`, `web` or `n8n` services through Docker
network membership. Application data still requires server-side role isolation.

The existing standalone `compose.production.yaml` is unchanged and remains
for a hotel deployed on its own VM. Shared-edge mode uses additive overlay
`compose.marina-customer-shared-edge.yaml`, which profiles the old standalone
Caddy out and adds a private `customer_gateway` preserving the current public,
admin, staff, API, media and n8n routing.

## Generate configuration (no services started)

Keep real `.env` outside Git. Each customer config needs the same true
`MARINA_DEPLOYMENT_HOST_ID` when installed on one Ubuntu, and unique
`COMPOSE_PROJECT_NAME`, `PROPERTY_CODE`, data/backup roots, secrets and hostnames.
`COOKIE_SECURE=true`; `MARINA_TENANT_CONTEXT_ENABLED=false`.

```bash
python3 scripts/marina_shared_edge_config.py \
  --out-dir /secure/marina-edge-config \
  /secure/hotel-a/.env.production \
  /secure/hotel-b/.env.production
```

The generator **fails closed** on reused hostnames, project IDs, storage,
backup trees, or critical credentials. Its output contains hostname-based
Caddy routes and one edge Compose graph. It does not copy credentials.

Check individual hotel Compose graphs **before** touching any running services:

```bash
docker compose --env-file /secure/hotel-a/.env.production \
  -p <hotel-a-project> -f compose.production.yaml \
  -f compose.marina-customer-shared-edge.yaml config
docker compose --env-file /secure/hotel-b/.env.production \
  -p <hotel-b-project> -f compose.production.yaml \
  -f compose.marina-customer-shared-edge.yaml config
```

The overlay's `caddy` uses profile `standalone-only` and must not run.
Only `customer_gateway` is attached to each project's private ingress.
The generated edge Compose graph must list all customer ingress networks as
`external: true`; they are first created by the customer Compose projects.
**Never** run `docker compose up` or switch public DNS based solely on this
document or green static CI.

## Runtime acceptance REQUIRED before any customer traffic

1. On a disposable/staging Ubuntu, use two synthetic hotel properties and two isolated PostgreSQL data directories. Keep all API/DB ports internal.
2. Check host listeners: **exactly one** shared edge publishes 80/443; no gateway/DB host ports.
3. Confirm edge TLS for each hostname, CORS, secure cookies, WebSockets and media; validate independent routes to A and B.
4. Confirm Docker network membership: gateway A has no route to gateway B, B's application containers or PostgreSQL; vice versa. Edge is the **only** proxy attached to both ingress networks.
5. Create staff/guest fixtures separately, reject foreign credentials/resources and unauthorized role changes, and verify Guest QR only resolves its own hotel.
6. Perform independent backup → clean restore into a disposable database for A and B. Ensure A restoration does not touch B, including media and n8n state.
7. Test single-hotel mobile login on a real Android device and revoke/logout.
8. Confirm provider credentials, WhatsApp message routing and MARINA AI knowledge isolation per customer.
9. Record monitored availability, load/resource limits, failure behavior and a tested rollback before approving first client launch.

**Known limits:** this scheme is network-level separation, NOT hard multi-tenant sandboxing: a compromised shared host/edge administrator remains privileged. Independent VMs offer stronger host isolation. CI only validates files and rendered Docker Compose graphs, not true runtime isolation, provider delivery or production readiness.
