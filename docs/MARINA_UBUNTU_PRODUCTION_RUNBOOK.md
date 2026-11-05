# MARINA SMART — isolated Ubuntu deployment package

Status: repository package and synthetic CI contract only. It has not been applied to the AI PROF KG Ubuntu host, a customer server, DNS, or a live database.

## Topology and isolation

Each hotel uses its own Compose project, PostgreSQL database, host data directory, Docker networks, Caddy state, and hostname set. The platform remains in one isolated application stack per hotel; `MARINA_TENANT_CONTEXT_ENABLED` stays `false`. PostgreSQL has no published host port. Only Caddy publishes TCP 80/443 and UDP 443.

The stack contains Caddy, PostgreSQL 16.15, the committed Prisma migration runner, the guarded one-shot empty-property/OWNER provisioner, MARINA API, public web, Admin, Staff PWA, and pinned n8n. Payments, MKassa, and service-point QR mutations are disabled. OTA credentials and payment credentials are not fabricated or enabled here.

Application and one-shot tool images use `marina-<slug>-<service>:<MARINA_RELEASE_SHA>` tags. A new release uses different image names, preserving the prior release tags for application rollback. Tags identify the intended revision; source checkout and image IDs must also be recorded. Do not prune prior release images before acceptance.

The deployment graph is defined in `compose.marina-production.yaml`, Caddy routes in `deploy/marina/Caddyfile`, and the environment template in `.env.marina-production.example`. These files do not inherit Three Crowns hostnames, property identifiers, or `/srv/three-crowns` paths.

## Host contract

Default per-hotel paths:

- checkout and operational files: `/srv/marina-smart/<slug>`;
- persistent PostgreSQL, media, n8n data: `/srv/marina-smart/<slug>/data`;
- local backup points: `/srv/marina-smart/<slug>/backups`.

The host check uses simple requirements: Linux, a supported 64-bit architecture, a usable Docker Engine, and Docker Compose. It reports CPU, RAM, free disk, ports, services, and target path for planning; it does not enforce generic CPU/RAM/disk minimums. Actual capacity is checked against the selected workload during acceptance. The non-destructive host probe accepts `HOST_PREFLIGHT_ROOT` and `HOST_PREFLIGHT_LABEL`.

Example probe after replacing `<slug>` with the intended unique hotel slug:

```bash
HOST_PREFLIGHT_LABEL='MARINA SMART Ubuntu preflight' \
HOST_PREFLIGHT_ROOT='/srv/marina-smart/<slug>' \
bash scripts/host_preflight.sh
```

`BLOCKED` means a core Linux, architecture, Docker, or Compose check failed. An occupied TCP 80/443 or UDP 443 listener matters only when planning public Caddy ingress; identify it before starting that ingress. The script reports running Docker containers, ports, resource figures, and active network services without reading container environments or changing state. Preserve existing services. It does not install, stop, or overwrite anything.

## Domain contract

Set the dedicated hotel domain and these records to the chosen Ubuntu public IP:

- `MARINA_PUBLIC_HOST` — hotel website;
- `www.<MARINA_PUBLIC_HOST>` — alias redirected by Caddy;
- `MARINA_ADMIN_HOST` — `admin.<MARINA_PUBLIC_HOST>`;
- `MARINA_STAFF_HOST` — `staff.<MARINA_PUBLIC_HOST>`;
- `MARINA_API_HOST` — `api.<MARINA_PUBLIC_HOST>`;
- `MARINA_AUTOMATION_HOST` — `automation.<MARINA_PUBLIC_HOST>`.

All five configured hosts must be distinct. Do not change DNS or point the production apex as part of this repository stage. Caddy requests certificates after the host has correct public DNS and reachable ingress.

## First installation sequence

1. On the approved Ubuntu host, create `/srv/marina-smart/<slug>` for the checkout and `/srv/marina-smart/<slug>/data/{postgres,media/public,n8n}` with restrictive permissions. Do not reuse another hotel's directory. The pinned n8n image runs as its unprivileged `node` user; inspect the image UID with `docker run --rm --entrypoint id n8nio/n8n:2.37.10` and grant that UID write access only to this hotel's `data/n8n` directory. Keep `media/public` readable by the Caddy container.
2. Put the tested release checkout in that directory. Copy `.env.marina-production.example` to `.env.marina-production` and set permissions to `600`.
3. Fill the exact host, property, tenant, and path values. Set `MARINA_RELEASE_SHA` to the exact 40-character Git commit SHA tested by CI. Generate separate 32+ character URL-safe PostgreSQL, automation service, and n8n encryption secrets. Do not put an owner's password in the environment file.
4. Configure the selected private S3-compatible off-site backup target before treating this as production-ready: `OFFSITE_BACKUP_REQUIRED=true`, HTTPS endpoint, region, private bucket, dedicated credentials, and `S3_BACKUP_PREFIX=marina/<slug>`. Do not reuse `three-crowns/production` or another hotel's prefix. Keep credentials in the mode-600 environment file and restrict the key to this bucket/prefix.
5. Run the static environment gate:

   ```bash
   python3 scripts/marina_production_preflight.py --env-file .env.marina-production
   ```

6. Run the host probe above and retain its output. Do not proceed if a core check is `BLOCKED`. Review port ownership before public ingress; create the selected persistent path during deployment with operator privileges.
7. Start only the private PostgreSQL service and wait until healthy:

   ```bash
   docker compose --env-file .env.marina-production -f compose.marina-production.yaml up -d postgres
   ```

8. Apply the committed migrations. This command is repeatable; it uses Prisma `migrate deploy`, not `db push`:

   ```bash
   docker compose --env-file .env.marina-production -f compose.marina-production.yaml run --rm migrate
   ```

9. In a protected operator shell, provide the one-time owner credential without writing it to `.env.marina-production` or shell history. Then run the bootstrap preflight and the isolated bootstrap profile:

   ```bash
   export MARINA_PROVISION_CONFIRM=CREATE_ONE_EMPTY_MARINA_PROPERTY
   export MARINA_OWNER_USERNAME='chosen-owner-login'
   read -rsp 'Initial MARINA owner password: ' MARINA_OWNER_PASSWORD; export MARINA_OWNER_PASSWORD; echo
   python3 scripts/marina_production_preflight.py --env-file .env.marina-production --bootstrap
   docker compose --env-file .env.marina-production --profile bootstrap -f compose.marina-production.yaml run --rm provision
   unset MARINA_PROVISION_CONFIRM MARINA_OWNER_USERNAME MARINA_OWNER_PASSWORD
   ```

   This action is intentionally one-shot. It refuses any database with rows in public application tables, validates the exact confirmation and dedicated `marina_` database, and rolls back all inserts on error. It creates an empty direct rate plan and product settings with optional modules disabled, plus one OWNER account. It does not import hotel rooms, guest records, prices, reservations, payments, or synthetic inventory.

10. Start the application and edge services:

   ```bash
   docker compose --env-file .env.marina-production -f compose.marina-production.yaml up -d --build
   docker compose --env-file .env.marina-production -f compose.marina-production.yaml ps
   ```

11. Verify all four web/API origins over HTTPS, log in as the new OWNER, check `/health/ready`, and confirm that rooms, rates, guest history and booking operations match only this hotel's approved data. Add actual inventory through the verified hotel setup workflow; never use synthetic seed scripts for a live hotel.

## Backup and rollback

Before any release update, use the existing reviewed backup script with this hotel's paths:

```bash
ROOT_DIR=/srv/marina-smart/<slug> \
BACKUP_DIR=/srv/marina-smart/<slug>/backups \
ENV_FILE=/srv/marina-smart/<slug>/.env.marina-production \
COMPOSE_FILE=/srv/marina-smart/<slug>/compose.marina-production.yaml \
bash /srv/marina-smart/<slug>/scripts/production_backup.sh
```

The backup contains the PostgreSQL dump and available media/n8n archives, a checksum manifest, and a success receipt. With the required S3 configuration, the shared script uploads each artifact beneath the Marina-specific prefix and verifies each object with a HEAD request. Before production acceptance, perform a clean restore rehearsal from the off-host copy on a separate disposable MARINA database. Application rollback and database restore are separate decisions; do not reverse migrations by improvising SQL.

The backup script has been tested synthetically, but off-host retention policy, Ubuntu systemd scheduling, disk/health alerts, and an observed restore on the actual target still require explicit verification before go-live.


## Application update and rollback boundary

Use the same hotel directory, Compose project, environment file and data paths for
both releases. Before building, check `git rev-parse HEAD` against the intended
`MARINA_RELEASE_SHA`; the static environment gate validates the SHA format but
cannot prove which source was checked out.

Before an update, record the current application container image IDs and release
tag, retain that source checkout and its Compose configuration, and complete the
backup/isolated-restore gate above. Never run `docker image prune -a`,
`docker compose down -v` or remove this hotel's data to perform an update.

An application-only rollback is allowed only after the previous application has
been verified compatible with the database schema and data now in use. It does
not reverse migrations. From the retained prior release checkout, with the same
hotel configuration, set the exact previously recorded SHA in the protected
operator shell:

```bash
export MARINA_RELEASE_SHA='<previous-tested-40-character-SHA>'
docker compose --env-file .env.marina-production -f compose.marina-production.yaml config --images
```

Confirm that all four previous application images already exist locally; do not
silently rebuild them from the newer checkout:

```bash
for service in api web admin staff; do
  image="marina-${MARINA_INSTANCE_SLUG}-${service}:${MARINA_RELEASE_SHA}"
  docker image inspect "$image" --format '{{.Id}}'
done
```

The loop requires `MARINA_INSTANCE_SLUG` to be set to the same hotel slug in the
operator shell. Compare each image ID with the recorded pre-update value. If an
image is absent or differs, stop and recover the verified release images first.
After compatibility and image identity have been confirmed:

```bash
docker compose --env-file .env.marina-production -f compose.marina-production.yaml up -d --no-build --pull never --no-deps api web admin staff
unset MARINA_RELEASE_SHA
```

This command targets only the four application services, without rerunning the
migration/provision services or recreating PostgreSQL, n8n or Caddy. Verify HTTPS,
owner/staff login, guest access, availability, booking conflicts and Admin WSS.
Keep the rollback SHA in the environment file only after acceptance, so the next
ordinary Compose invocation does not restore the newer release unintentionally.

If schema compatibility is not established, stop writes and use the separately
reviewed database recovery procedure on an isolated target. Do not run a
destructive live database restore as an automatic response to an application
failure. These are repository instructions; no host rollback has been performed.

## Release and final acceptance gates

For each update: capture and verify backup; record the running commit; validate environment and Compose; run migration checks; build from the tested commit; restart services; verify health, login, booking availability, Admin WebSocket and public/staff interfaces; retain the previous release until acceptance.

This repository package is not production acceptance by itself. Before live use, verify on the actual isolated staging host:

- host capacity, Docker, port ownership and persistent path permissions;
- DNS, automatic TLS, HTTPS and Admin WSS;
- first-owner login and session cookie through the real proxy;
- one hotel's data remains isolated from every other hotel;
- backup, off-host copy, clean restore and rollback;
- real inventory setup and full booking/check-in/check-out flow;
- monitoring, disk capacity and restart recovery;
- no payment or OTA action is presented as connected until its official provider integration is configured and tested.

No deployment, DNS update, production migration, customer data import, or live booking was performed while preparing this package.
