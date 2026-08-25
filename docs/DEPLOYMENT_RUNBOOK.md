# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Date: 2026-08-26
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
- owner bootstrap credentials delivered out-of-band and cleared after bootstrap;
- long random n8n/Resort Core service secret;
- Telegram/OpenAI credentials only if the corresponding staff automation is activated;
- owned public-site media.

V1 does **not** require an automated acquiring/payment provider. The manager decides and collects prepayment manually; Resort OS records only manager-confirmed internal payment facts.

Never commit real secrets.

## 3. Hard production blockers

Do not cut over production while any of these remain unresolved:

1. Current `main` has not been executed through an accepted verification path after the GitHub Actions runner issue.
2. Database migration history is not yet a production-grade Prisma migration chain. Development currently uses schema bootstrap/db-push plus explicit SQL constraints. Before production, create and rehearse a baseline migration in staging.
3. Backup + clean restore has not been rehearsed against the current schema.
4. Public-site temporary/hotlinked media has not been replaced with owned Three Crowns assets.
5. Final DNS/TLS/hostnames have not been approved.
6. Monitoring/rollback acceptance has not been completed.

Automated acquiring is intentionally not a V1 production blocker under the current owner-approved manager-prepayment workflow.

## 4. Local release-candidate verification

While GitHub Actions jobs are being created but fail before executing steps (`steps=null`), run the repository-local verifier before staging/demo:

```bash
bash scripts/release_candidate_check.sh
```

Optional synthetic presentation data after the check:

```bash
RC_SEED_DEMO=1 bash scripts/release_candidate_check.sh
```

The local check validates/builds the canonical applications and Core development baseline. It does not replace the production migration/backup/staging gates.

Presentation sequence and acceptance wording:

`docs/DEMO_ACCEPTANCE_2026-08-26.md`.

## 5. Staging sequence

Use a clean staging database.

1. Copy `.env.production.example` to a host-only `.env.production` and replace all placeholders.
2. Create a database backup location before loading any real import.
3. Build images:

```bash
docker compose --env-file .env.production -f compose.production.yaml build
```

4. Prepare database schema in staging using the current canonical Prisma schema and `packages/database/sql/*.sql`.

IMPORTANT: until a migration baseline is generated, this is a staging bootstrap procedure, not the approved production migration mechanism.

5. Load the evidence-backed Three Crowns seed only into an empty/staging property database.

The seed must continue to reconcile to exactly 84 rooms and 12 categories.

6. Bootstrap the first OWNER account out-of-band with `scripts/bootstrap_owner.py`, then clear `BOOTSTRAP_OWNER_PASSWORD` before production preflight.
7. Start containers:

```bash
docker compose --env-file .env.production -f compose.production.yaml up -d
```

8. Verify Core canonical probes:

- `/health/live` returns process liveness;
- `/health/ready` returns database/property readiness and inventory counts;
- legacy `/live` and `/ready` remain compatibility aliases only;
- `/api/v1/booking/check-availability` returns seeded inventory;
- unauthenticated PMS/admin endpoints reject access;
- authenticated OWNER can open Command Center, chessboard, requests, reservations, finance and operations.

9. Verify one isolated booking lifecycle in staging using test dates/data only:

`ReservationRequest -> manager quote -> manager-confirmed internal payment -> GUARANTEED -> chessboard move/resize -> check-in -> optional relocation -> check-out -> housekeeping`.

10. Verify public-site inventory reflects chessboard mutations from the same Core data without a separate synchronization job.

11. Verify staff roles independently:

- MAID cannot access manager data;
- TECHNICIAN cannot access manager data;
- each role sees only allowed operational task types/actions.

## 6. Database migration gate

Before first production cutover create an immutable migration baseline from the current canonical schema and SQL modules.

Required evidence:

- empty DB -> migrations -> expected schema;
- backup -> migration -> application smoke test;
- rollback/restore from backup;
- constraint checks including `no_overlapping_active_room_blocks`.

Do not substitute `prisma db push` for the long-term production migration process.

## 7. Backup/restore gate

Minimum production policy must define:

- backup frequency;
- retention;
- encrypted storage location;
- restore owner;
- restore procedure;
- last successfully tested restore date.

A backup is not considered operational until a clean restore has been tested and `LAST_VERIFIED_BACKUP_AT` is recorded for preflight.

## 8. Host routing

The containers bind to loopback ports by default in `compose.production.yaml`:

- web: `127.0.0.1:3000`;
- admin: `127.0.0.1:3001`;
- staff: `127.0.0.1:3002`;
- API: `127.0.0.1:8000`.

A deployment reverse proxy/load balancer should terminate HTTPS and route approved hostnames to these services. Exact hostnames remain a deployment decision and are not hard-coded here.

## 9. Cookie/CORS rule

Production must use HTTPS (`COOKIE_SECURE=true`).

`CORS_ORIGINS` must contain only exact approved UI origins.

Set `COOKIE_DOMAIN` only when shared staff/admin/API session cookies across subdomains are intentionally required and tested.

## 10. n8n boundary

Production n8n must use `AUTOMATION_SERVICE_KEY` and Resort Core APIs.

n8n must not:
- write PostgreSQL directly;
- create guaranteed Reservation directly;
- decide/confirm prepayment;
- check-in/check-out/refund;
- invent price, availability or policy.

Current channel path:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n.

## 11. Observability minimum

Before production approval require:

- API/app error logs with request IDs/timestamps;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup failure alerting;
- HTTP 5xx visibility;
- AuditLog retention appropriate to operational needs.

No external monitoring vendor is mandated by this document.

## 12. Public-site cutover gate

Before moving `3korony.com`:

- owned logo/media installed;
- room catalog reviewed against canonical inventory;
- current rates/business copy approved;
- booking request path tested end-to-end;
- mobile review complete;
- existing site rollback target preserved;
- DNS TTL reduced in advance if appropriate;
- rollback instructions written and tested.

## 13. Production cutover

Only after staging acceptance and backup/migration gates:

1. take a fresh pre-cutover backup;
2. run `scripts/production_preflight.py` successfully;
3. deploy exact reviewed commit/image set;
4. run readiness/smoke tests;
5. switch routing/DNS;
6. verify booking request from public site;
7. verify manager login/PMS/chessboard;
8. verify staff login/tasks;
9. watch errors and database health;
10. keep rollback available throughout the acceptance window.

## 14. Rollback

Rollback application code by redeploying the previously accepted image/commit.

If a database change is involved, do not improvise reverse SQL in production. Restore using the rehearsed migration rollback/backup procedure appropriate to that release.

DNS rollback should point traffic to the preserved previous public target when required.

## 15. Current verification caveat

GitHub Actions currently creates workflow runs, but observed jobs terminate within seconds with `steps=null` and no downloadable job logs. This is not valid evidence of a test-step failure because no workflow step executed.

Until runner execution is restored, latest changes remain `IMPLEMENTED / NOT CI-VERIFIED` unless explicit local/staging verification evidence is captured.
