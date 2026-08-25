# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Date: 2026-08-25
Status: PREPARED / NOT YET PRODUCTION EXECUTED

This document defines a deployment path. It is not evidence that production deployment has happened.

## 1. Deployment units

Current container topology:

- PostgreSQL 16;
- FastAPI Resort Core (`api`);
- public Next.js site (`web`);
- PMS/admin Next.js application (`admin`);
- staff Next.js PWA (`staff`).

Source: `compose.production.yaml`.

NFC is outside the active deployment scope.

## 2. Required production inputs

Before deployment provide only real infrastructure/configuration values:

- deployment host or platform;
- PostgreSQL credentials/storage;
- final public/admin/staff/API hostnames;
- HTTPS/TLS termination;
- owner bootstrap credentials delivered out-of-band;
- Telegram bot token only when Telegram staff integration is activated;
- automation service secret only when n8n is activated;
- payment-provider credentials only after provider selection and webhook contract approval;
- owned public-site media.

Never commit these values.

## 3. Hard production blockers

Do not cut over production while any of these remain unresolved:

1. Current `main` has not been re-verified after the GitHub Actions runner issue.
2. Database migration history is not yet a production-grade Prisma migration chain. Development currently uses schema bootstrap/db-push plus explicit SQL constraints. Before production, create and rehearse a baseline migration in staging.
3. Backup + restore has not been rehearsed against a production-like database.
4. Public-site temporary/hotlinked media has not been replaced with owned assets.
5. Final payment provider/webhook verification is not implemented if automated online payment is required at launch.
6. Final DNS/TLS/hostnames have not been approved.

## 4. Staging sequence

Use a clean staging database.

1. Copy `.env.production.example` to a host-only `.env.production` and replace all placeholders.
2. Create a database backup location before loading any real import.
3. Build images:

```bash
docker compose --env-file .env.production -f compose.production.yaml build
```

4. Prepare database schema in staging using the current canonical Prisma schema and `packages/database/sql/*.sql`.

IMPORTANT: until a migration baseline is generated, this is a staging bootstrap procedure, not the approved production migration mechanism.

5. Load the evidence-backed Three Crowns seed only into an empty/staging property database:

```bash
python scripts/seed_from_intake.py
```

The seed must continue to reconcile to 84 rooms and 12 categories.

6. Bootstrap the first OWNER account out-of-band with `scripts/bootstrap_owner.py`.
7. Start containers:

```bash
docker compose --env-file .env.production -f compose.production.yaml up -d
```

8. Verify Core:

- `/live` returns process liveness;
- `/ready` returns database/property readiness and inventory counts;
- `/api/v1/booking/check-availability` returns real seeded inventory;
- unauthenticated PMS/admin endpoints reject access;
- authenticated OWNER can open Command Center, grid, requests, reservations and operations.

9. Verify one isolated booking lifecycle in staging using test dates/data only:

`ReservationRequest -> quote -> controlled confirmed payment -> GUARANTEED -> check-in -> check-out -> housekeeping task`.

10. Verify staff roles independently:

- MAID cannot access manager data;
- TECHNICIAN cannot access manager data;
- each role sees only allowed operational task types/actions.

## 5. Database migration gate

Before first production cutover create an immutable migration baseline from the current canonical schema and SQL modules.

Required evidence:

- empty DB -> migrations -> expected schema;
- backup -> migration -> application smoke test;
- rollback/restore from backup;
- constraint checks including no overlapping active room blocks.

Do not substitute `prisma db push` for the long-term production migration process.

## 6. Backup/restore gate

Minimum production policy must define:

- backup frequency;
- retention;
- encrypted storage location;
- restore owner;
- restore procedure;
- last successfully tested restore date.

A backup is not considered operational until a restore has been tested.

## 7. Host routing

The containers bind to loopback ports by default in `compose.production.yaml`:

- web: `127.0.0.1:3000`;
- admin: `127.0.0.1:3001`;
- staff: `127.0.0.1:3002`;
- API: `127.0.0.1:8000`.

A deployment reverse proxy/load balancer should terminate HTTPS and route approved hostnames to these services. Exact hostnames are a deployment decision and are not hard-coded here.

## 8. Cookie/CORS rule

Production must use HTTPS (`COOKIE_SECURE=true`).

`CORS_ORIGINS` must contain only exact approved UI origins.

Set `COOKIE_DOMAIN` only when shared staff/admin/API session cookies across subdomains are intentionally required and tested.

## 9. Observability minimum

Before production approval require:

- API/app error logs with timestamps;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup failure alerting;
- HTTP 5xx visibility;
- audit-log retention appropriate to operational needs.

No external monitoring vendor is mandated by this document.

## 10. Public-site cutover gate

Before moving `3korony.com`:

- owned logo/media installed;
- room catalog reviewed against canonical inventory;
- current rates/business copy approved;
- booking request path tested end-to-end;
- mobile review complete;
- existing site rollback target preserved;
- DNS TTL reduced in advance if appropriate;
- rollback instructions written and tested.

## 11. Production cutover

Only after staging acceptance and backup/migration gates:

1. take a fresh pre-cutover backup;
2. deploy exact reviewed commit/image set;
3. run readiness/smoke tests;
4. switch routing/DNS;
5. verify booking request from public site;
6. verify manager login/PMS;
7. verify staff login/tasks;
8. watch errors and database health;
9. keep rollback available throughout the acceptance window.

## 12. Rollback

Rollback application code by redeploying the previously accepted image/commit.

If a database change is involved, do not improvise reverse SQL in production. Restore using the rehearsed migration rollback/backup procedure appropriate to that release.

DNS rollback should point traffic to the preserved previous public target when required.

## 13. Current verification caveat

GitHub Actions has recently produced jobs that fail before any workflow step starts (`steps=null`). Until runner execution is restored, changes after the last confirmed green baseline remain IMPLEMENTED / NOT CI-VERIFIED unless another explicit verification source exists.
