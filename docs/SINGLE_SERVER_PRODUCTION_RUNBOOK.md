# Three Crowns — Single Server Production Runbook

Status: deployment procedure for the approved simple topology.

## 1. Target topology

One VPS/VDS with Docker and one public IPv4 hosts the complete active Resort OS contour:

- `3korony.com` -> public Next.js web;
- `admin.3korony.com` -> PMS/Admin Next.js;
- `staff.3korony.com` -> Staff PWA;
- `api.3korony.com` -> FastAPI Resort Core;
- `automation.3korony.com` -> n8n;
- PostgreSQL remains private inside the Docker network;
- public media lives under host persistent storage;
- backups are written outside container layers and copied off-site.

Canonical truth boundary remains:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

n8n, Google Drive and Google Sheets are not alternative booking/inventory/payment authorities.

## 2. Minimum host requirements

Recommended initial production host:

- Ubuntu 24.04 LTS or equivalent supported Linux;
- 4 vCPU;
- 8 GB RAM;
- 120–160 GB NVMe/SSD;
- static public IPv4;
- root or sudo SSH access;
- Docker Engine + Docker Compose plugin;
- provider snapshot capability strongly preferred.

Only ports 80/443 should be public for the application. SSH must be restricted by key-based access/firewall policy. PostgreSQL must not be exposed to the public internet.

## 3. Persistent host layout

Recommended root:

`/srv/three-crowns`

Persistent data:

- `/srv/three-crowns/data/postgres`;
- `/srv/three-crowns/data/n8n`;
- `/srv/three-crowns/data/media/public`;
- `/srv/three-crowns/data/media/private`;
- `/srv/three-crowns/backups`.

The Git checkout may be replaced during deployment. The data and backup directories must not be deleted with the checkout.

## 4. DNS before launch

All required names point to the same server IP:

- apex `3korony.com`;
- `www.3korony.com`;
- `admin.3korony.com`;
- `staff.3korony.com`;
- `api.3korony.com`;
- `automation.3korony.com`.

Do not switch the live apex until external staging/acceptance and rollback criteria are satisfied. A staging subdomain may be used first with the same topology.

## 5. Secrets and environment

Copy `.env.production.example` to `.env.production` on the server only.

Generate independent strong values for:

- `POSTGRES_PASSWORD`;
- `AUTOMATION_SERVICE_KEY`;
- `N8N_ENCRYPTION_KEY`;
- staff/Telegram webhook secrets when enabled;
- OpenAI/provider secrets when enabled.

Never commit `.env.production` or copy it into ordinary backup archives.

Before production cutover, replace the n8n `latest` image reference with an explicitly tested pinned version.

## 6. First deployment sequence

1. Put the intended release commit on the server.
2. Create persistent host directories and restrict permissions.
3. Create `.env.production` with final hosts and secrets.
4. Validate the graph with Docker Compose config.
5. Start PostgreSQL only.
6. Apply the committed Prisma migration chain with `prisma migrate deploy` from the repository/tooling contour.
7. Run production preflight and verify the migration ledger.
8. Import/reconcile the physical room register only after all required owner confirmations are complete.
9. Build application images.
10. Start API, web, admin and staff.
11. Start n8n only after Core is healthy.
12. Start Caddy last; verify automatic TLS issuance.
13. Run external staging/production acceptance against HTTPS/WSS origins.

No clean install may use `prisma db push` as a substitute for the committed production migration chain.

## 7. Required acceptance before DNS cutover

Must be explicitly proven:

- `https://3korony.com` returns the canonical current site;
- `https://admin.3korony.com` returns PMS/Admin;
- `https://staff.3korony.com` works on real iPhone and Android browsers;
- Telegram Mini App authentication/flow works when enabled;
- `https://api.3korony.com/health/ready` is healthy;
- secure session cookies work through real HTTPS;
- exact CORS origins work and unapproved origins fail;
- PMS WebSocket upgrades through public WSS;
- availability/pricing comes from Core;
- website creates `ReservationRequest`, not guaranteed Reservation;
- PMS move/resize/split/conflict controls remain server authoritative;
- PostgreSQL is not publicly reachable;
- NFC/beach routes remain absent from active OpenAPI;
- backup -> clean restore verification is recent.

## 8. Backups

`scripts/production_backup.sh` creates:

- PostgreSQL logical dump;
- media archive when present;
- n8n persistent-state archive when present;
- SHA-256 manifest.

Recommended policy:

- nightly local backup;
- at least 14 daily local restore points initially;
- provider VPS snapshots;
- copy backup directories to an off-site destination such as the Three Crowns Google Drive backup area.

Google Drive is an off-site archive/control layer, not live hotel database truth.

A backup is not considered verified until a clean restore has been tested.

## 9. Update procedure

For every release:

1. take a fresh backup;
2. record current running Git commit and image state;
3. fetch the intended release;
4. run migration/preflight checks;
5. build images;
6. replace containers;
7. run health and smoke acceptance;
8. keep the previous release/backup as the rollback point until acceptance completes.

Do not mutate production schema manually from a SQL console except under an explicit reviewed incident procedure.

## 10. Rollback principle

Application rollback and database rollback are separate decisions.

If no irreversible migration/data mutation occurred, restore the previous application release.

If database state must be reverted, stop writes and use the reviewed backup/restore procedure. Never improvise destructive reverse SQL during an incident.

## 11. Operating model

Daily users only need:

- `3korony.com` for guests;
- `admin.3korony.com` for management/reception;
- `staff.3korony.com` or Telegram for staff;
- Google Drive for documents/original files/report exports.

GitHub, Docker, PostgreSQL internals and n8n administration are engineering/operations surfaces, not normal hotel workflows.

## 12. Remaining non-code gates

Even with this package complete, production cutover remains blocked until:

1. the actual purchased hosting is confirmed to be a VPS/VDS capable of Docker/root access;
2. the 84-room physical register has owner-approved P0 facts;
3. external HTTPS/WSS acceptance succeeds;
4. real-device acceptance succeeds;
5. final backup/restore, secrets, DNS and rollback evidence is recorded.
