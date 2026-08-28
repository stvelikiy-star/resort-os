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

### Mandatory first action on the purchased host

Run the non-destructive infrastructure probe before installing, stopping or replacing anything:

`bash scripts/host_preflight.sh`

The probe reports OS/architecture, CPU, RAM, disk, root/sudo, Docker/Compose, outbound registry reachability, current 80/443 listeners, a possible 5432 listener and the `/srv/three-crowns` layout capability. It does not mutate the host.

Interpretation:

- `PASS` — checked infrastructure requirements are satisfied;
- `PASS WITH WARNINGS` — proceed only after warnings are understood/resolved;
- `BLOCKED` — do not attempt Resort OS deployment until mandatory requirements are fixed.

An existing listener on 80/443 is expected while the legacy `3korony.com` site is live and is a warning, not permission to stop it.

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

## 4. Preserve the currently live site before any cutover

The existing `3korony.com` must be treated as live production until Resort OS acceptance is complete.

Before changing its web-server configuration or apex DNS:

1. record the current public DNS/IP and active web service;
2. record the current document root/site configuration where access permits;
3. create a complete copy/archive of the current site files and relevant server configuration;
4. record the checksum and storage location of that archive;
5. if the current site has a database, export it separately and test that the export is readable;
6. keep the current site serving while the new system is validated on staging/subdomains;
7. define the exact rollback action before changing the apex route.

Do not delete or overwrite the legacy site merely because the new containers build successfully.

## 5. DNS before launch

All required names ultimately point to the same server IP:

- apex `3korony.com`;
- `www.3korony.com`;
- `admin.3korony.com`;
- `staff.3korony.com`;
- `api.3korony.com`;
- `automation.3korony.com`.

Do not switch the live apex until external staging/acceptance and rollback criteria are satisfied. Use staging hostnames first when the current apex is serving the legacy site.

## 6. Secrets and environment

Copy `.env.production.example` to `.env.production` on the server only.

Generate independent strong values for:

- `POSTGRES_PASSWORD`;
- `AUTOMATION_SERVICE_KEY`;
- `N8N_ENCRYPTION_KEY`;
- staff/Telegram webhook secrets when enabled;
- OpenAI/provider secrets when enabled.

Never commit `.env.production` or copy it into ordinary backup archives.

The production baseline pins `n8nio/n8n:2.36.2`, a known patched 2.x release. Do not replace it with `latest`; upgrade n8n only through an explicit tested release change.

## 7. First deployment sequence

1. Run `scripts/host_preflight.sh` and retain its evidence.
2. Preserve the currently live site and record its rollback point.
3. Put the intended tested Resort OS release commit on the server without overwriting legacy files.
4. Create persistent host directories and restrict permissions.
5. Create staging/production environment files with correct hosts and independent secrets.
6. Validate the graph with Docker Compose config.
7. Start the isolated PostgreSQL container only.
8. Apply the committed Prisma migration chain with `prisma migrate deploy` from the repository/tooling contour.
9. Run database/application production preflight and verify the migration ledger.
10. Import/reconcile the physical room register only after all required owner confirmations are complete.
11. Build application images from the pinned dependency tree/release commit.
12. Start API, web, admin and staff in the non-apex acceptance contour.
13. Start n8n only after Core is healthy.
14. Start/route Caddy for the approved staging hostnames and verify automatic TLS issuance.
15. Run external staging acceptance against HTTPS/WSS origins.
16. Complete real iPhone/Android/Telegram acceptance.
17. Take and verify a fresh backup/restore point.
18. Only after all gates pass, perform controlled apex cutover to `3korony.com`.

No clean install may use `prisma db push` as a substitute for the committed production migration chain.

## 8. Required acceptance before DNS/apex cutover

Must be explicitly proven:

- staging public site returns the canonical current site before replacing the live apex;
- PMS/Admin returns the intended current interface;
- Staff PWA works on real iPhone and Android browsers;
- Telegram Mini App authentication/flow works when enabled;
- Core `/health/ready` is healthy through public HTTPS;
- secure session cookies work through real HTTPS;
- exact CORS origins work and unapproved origins fail;
- PMS WebSocket upgrades through public WSS;
- availability/pricing comes from Core;
- website creates `ReservationRequest`, not guaranteed Reservation;
- PMS move/resize/split/conflict controls remain server authoritative;
- PostgreSQL is not publicly reachable;
- NFC/beach routes remain absent from active OpenAPI;
- backup -> clean restore verification is recent;
- legacy-site rollback remains executable until acceptance is signed off.

After controlled cutover, repeat health/smoke checks on the real `3korony.com` origins.

## 9. Backups

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

## 10. Update procedure

For every release:

1. take a fresh backup;
2. record current running Git commit and image state;
3. fetch the intended release;
4. run migration/preflight checks;
5. build images from the committed lock/release state;
6. replace containers;
7. run health and smoke acceptance;
8. keep the previous release/backup as the rollback point until acceptance completes.

Do not mutate production schema manually from a SQL console except under an explicit reviewed incident procedure.

## 11. Rollback principle

Application rollback and database rollback are separate decisions.

If no irreversible migration/data mutation occurred, restore the previous application release.

If database state must be reverted, stop writes and use the reviewed backup/restore procedure. Never improvise destructive reverse SQL during an incident.

During the initial legacy-site replacement, rollback also includes restoring the previous web-server/apex route to the preserved old site if Resort OS cutover acceptance fails.

## 12. Operating model

Daily users only need:

- `3korony.com` for guests;
- `admin.3korony.com` for management/reception;
- `staff.3korony.com` or Telegram for staff;
- Google Drive for documents/original files/report exports.

GitHub, Docker, PostgreSQL internals and n8n administration are engineering/operations surfaces, not normal hotel workflows.

## 13. Remaining non-code gates

Even with the single-server package CI-verified, production cutover remains blocked until:

1. the actual purchased hosting passes `scripts/host_preflight.sh` (or is upgraded to a suitable VPS/VDS);
2. the currently live legacy site has a recorded backup/rollback point;
3. the 84-room physical register has owner-approved P0 facts;
4. external HTTPS/WSS acceptance succeeds;
5. real-device acceptance succeeds;
6. final backup/restore, secrets, DNS and rollback evidence is recorded.
