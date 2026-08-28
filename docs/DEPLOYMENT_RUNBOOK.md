# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Date: 2026-08-28
Status: PREPARED / CI-LOCAL STAGING VERIFIED / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION EXECUTED

This document defines the deployment and cutover procedure. It is **not** evidence that production deployment has happened.

Canonical factual Current State is maintained in `knowledge/04_CURRENT_STATE.md`.

---

## 1. Current deployment unit

Approved current one-server topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16, private to the deployment network;
- FastAPI Resort Core (`api`);
- public Next.js site (`web`);
- PMS/admin Next.js application (`admin`);
- staff Next.js PWA (`staff`);
- pinned n8n `2.36.2`;
- persistent PostgreSQL/media/n8n state;
- local backup directory with off-site copy expected.

NFC is outside the active Three Crowns V1 runtime.

Current package evidence is CI-only. It has not yet been deployed to the purchased external host.

---

## 2. Current audited repository evidence

Latest fully audited executable/package head before later documentation-only synchronization:

`19a1228530afcad59a0f3ce19c11f6238e88932a`.

Relevant successful CI evidence on that head / associated PR merge snapshot:

- Resort Core CI `33163003201`;
- Three Crowns Full Staging Gate `33163003277`;
- Single Server Production Package CI `33163003205`;
- Dependency Security Inspection `33163003236`;
- Production Migration Baseline CI `33163003229`;
- PostgreSQL Backup Restore CI `33163003219`;
- PMS Chessboard Mutation CI `33163003218`;
- Realtime PMS CI `33163003253`;
- Hotel Operations CI `33163003244`;
- Public Site Truth CI `33163003199`;
- AI Administrator CI `33163003186`.

Do not convert this CI evidence into a claim that the purchased host, external TLS/WSS, live providers, real devices or production DNS are verified.

---

## 3. Required external production inputs

Before external deployment, obtain only real infrastructure/configuration values:

- access to the purchased deployment host;
- host type/capability evidence from `scripts/host_preflight.sh`;
- final public/admin/staff/API hostnames and DNS control;
- PostgreSQL production credentials/storage paths;
- production HTTPS/TLS routing;
- owner bootstrap credentials delivered out-of-band and removed/rotated after bootstrap;
- long random n8n/Resort Core service secret;
- real OpenAI/API Green credentials only if those provider contours are explicitly activated for launch;
- owned final public media/content approval;
- owner-confirmed physical 84-room production register.

Never commit real secrets.

Automated acquiring/payment-provider integration is **not** a current Three Crowns V1 launch requirement. Manager chooses prepayment amount/terms/method and Resort OS records manager-confirmed payment facts.

---

## 4. Hard production blockers that remain open

Do not cut over production while any item below remains unresolved:

1. Purchased host has not passed non-destructive `scripts/host_preflight.sh`.
2. Existing live `3korony.com` has no verified full rollback backup in current project evidence.
3. Isolated external HTTPS/WSS staging has not been deployed and accepted on the real host/network.
4. External rendered public-truth probe has not passed against that staging URL.
5. Owner-confirmed physical 84-room register is incomplete.
6. Real browser/mobile/Telegram acceptance is incomplete.
7. Real website AI acceptance and, if launch-enabled, real provider/WhatsApp E2E are incomplete.
8. Fresh pre-cutover production backup/restore/preflight/secrets/DNS rollback evidence is absent.

Resolved historical blockers must not be reintroduced as current blockers:

- committed production migration chain exists (`0_init`, `1_site_content`);
- clean `prisma migrate deploy` is CI-verified;
- migration-aware backup -> clean restore is CI-verified;
- GitHub Actions currently execute real steps and provide valid current CI evidence;
- repository-local public truth and i18n guards are active;
- CI-local Docker staging is verified.

---

## 5. Non-destructive host capability gate

Before installing, stopping, replacing or reconfiguring anything on the purchased host, run:

```bash
bash scripts/host_preflight.sh
```

This script is intentionally non-destructive. It checks:

- Linux / supported architecture;
- CPU count;
- RAM;
- free disk;
- root/sudo capability;
- Docker Engine;
- Docker Compose plugin;
- outbound Docker registry reachability;
- current listeners on 80/443;
- host-level 5432 exposure;
- target persistent-path access;
- active nginx/apache/httpd/caddy services.

Interpretation:

- `RESULT: PASS` — infrastructure checks passed;
- `RESULT: PASS WITH WARNINGS` — do not cut over until warnings are understood/accepted;
- `RESULT: BLOCKED` — do not deploy this topology to that host.

Host preflight does not prove external staging or production correctness.

---

## 6. Preserve the current legacy site before deployment

The currently live site is a rollback dependency until the new system passes external acceptance.

Do not stop its web service, overwrite its document root, replace its database or switch DNS before a verified rollback point exists.

Because the actual hosting type/filesystem/control panel are currently UNKNOWN, do not invent backup commands or paths in advance.

Minimum evidence required from the real host/control panel:

- hosting provider/account identified;
- current DNS zone exported or recorded;
- current web root/app source archived;
- current legacy database dumped if one exists;
- uploads/media archived;
- current web-server/vhost configuration captured where accessible;
- current PHP/runtime/config values captured where relevant;
- backup checksum/size/timestamp recorded;
- restore target/procedure identified;
- rollback owner and maximum acceptable cutover window recorded.

A public HTML crawl alone is **not** a full rollback backup.

If the host is shared hosting and cannot support the approved Docker topology, preserve the legacy host as rollback while deploying Resort OS to a separate suitable VPS/VDS.

---

## 7. Production migration gate

Current committed migration chain:

- `0_init`;
- `1_site_content`.

Do not use `prisma db push` as the production migration mechanism.

Production procedure must use the committed migration chain and preserve evidence:

```bash
npx prisma migrate deploy
```

Required production evidence:

- backup taken before migration;
- exact reviewed release SHA/image set recorded;
- migration command/result captured;
- migration ledger captured;
- required critical constraints verified;
- application readiness/smoke checks passed;
- rollback/restore path remains available.

CI evidence proves the migration process in clean/isolated environments; it does not prove the production database has been migrated.

---

## 8. Backup / restore gate

Current repository backup/restore implementation has CI evidence, but production still needs a fresh real backup.

Before cutover define and record:

- backup frequency;
- retention;
- encrypted off-site storage location;
- restore owner;
- restore procedure;
- checksum/size;
- last successfully tested restore timestamp.

A production backup is not operational evidence until its restore path is proven for that production environment.

Never improvise destructive reverse SQL as a production rollback strategy.

---

## 9. External staging deployment

Use an isolated hostname/subdomain or otherwise isolated routing that does not replace the live apex site.

Do not point `3korony.com` apex traffic to the new stack during this stage.

High-level sequence:

1. Preserve legacy rollback evidence.
2. Pass `scripts/host_preflight.sh`.
3. Prepare host-only production/staging environment values with no secrets committed to Git.
4. Create persistent directories/volumes.
5. Start private PostgreSQL.
6. Apply committed migrations.
7. Load only evidence-backed staging/test data or approved production import according to the acceptance phase.
8. Bootstrap authorized test/owner users out-of-band.
9. Build/pull the exact reviewed release images.
10. Start Caddy + web/admin/staff/Core + n8n as required.
11. Keep PostgreSQL private.
12. Verify HTTPS/WSS, cookies, CORS, routing and health endpoints from outside the host.

Do not use the old Vercel preview/stub as a substitute for this external staging gate.

---

## 10. External staging acceptance

At minimum verify:

### Infrastructure

- public HTTPS is valid;
- HTTP redirects to HTTPS as intended;
- API readiness is healthy;
- WSS upgrade works from the real browser/Admin client;
- PostgreSQL is not publicly exposed;
- restart/persistence behavior is acceptable;
- logs are accessible;
- backup path is writable and monitored.

### Public site

- real Resort OS site renders, not a preview stub;
- RU/KG/EN surfaces behave correctly;
- room catalog/content is reviewed;
- availability/pricing uses Core;
- booking submission creates a `ReservationRequest`, not an automatic confirmed Reservation;
- no stale automatic prepayment/payment-provider claims appear.

Run the non-destructive external rendered-site truth probe against the staging URL:

```bash
python3 scripts/external_public_truth_probe.py https://<staging-host>/
```

A PASS verifies only the checked rendered response/URL. It does not prove all business flows.

### PMS / reservation lifecycle

Use isolated test data/dates and verify:

`ReservationRequest -> manager quote -> manager-confirmed payment fact -> Reservation -> chessboard -> check-in -> optional move/Split Stay -> check-out -> housekeeping`.

Also verify stale/conflict protection and realtime refresh from the real browser.

### Staff

- MAID/TECHNICIAN authorization boundaries;
- mobile task UI;
- housekeeping inspection/rework/acceptance;
- technician flow;
- real-device acceptance.

### AI / messaging

Website AI:
- real browser/mobile rendering;
- Core-direct availability/pricing;
- no Reservation/payment confirmation authority;
- provider-unavailable behavior;
- prompt-injection/adversarial content acceptance.

WhatsApp/API Green, only if activated for launch:
- real hotel number;
- provider credentials stored as secrets;
- webhook authenticity/secret handling;
- duplicate webhook/idempotency case;
- unavailable-date case;
- prompt-injection case;
- ReservationRequest-only authority.

---

## 11. PMS / chessboard acceptance boundary

The current V9 chessboard is not a presentation-only grid. Current CI already covers move/resize/Split Stay, stale conflict rejection, history preservation, housekeeping consequences and AuditLog.

External acceptance must prove the same behavior over the actual HTTPS/WSS network and real Admin browser.

Do not replace it with a separate parallel scheduling source of truth.

All mutations remain server-authoritative through Resort Core.

---

## 12. Public payment / sales truth boundary

Three Crowns V1 public copy must stay inside current approved business truth.

Do not publish or reintroduce without new owner-approved evidence:

- fixed 30% prepayment;
- automatic first-night prepayment rule;
- automatic two-day unpaid-hold rule;
- unverified online-card acquiring claim;
- unverified Elsom payment route;
- AI-generated payment links/QR/payment instructions.

The repository `scripts/public_site_truth_guard.py` fail-closes on these current stale/unapproved patterns.

Manager remains responsible for current V1 payment amount/terms/method and factual payment confirmation.

---

## 13. Cookie / CORS / authorization gate

Production must use HTTPS and secure cookie configuration.

`CORS_ORIGINS` must contain only exact approved UI origins.

Set a shared cookie domain only when intentionally required and externally tested.

Frontend visibility is not authorization. All role/resource mutation boundaries remain server-side.

External staging must prove cross-origin/session behavior from real browsers before cutover.

---

## 14. n8n / AI authority boundary

n8n and AI are clients of controlled Resort Core capabilities.

They must not:

- write PostgreSQL directly as a generic business interface;
- invent price/availability/policy;
- create guaranteed Reservation outside human confirmation;
- confirm payment;
- decide prepayment amount/method;
- check-in/check-out/refund without an explicitly approved controlled capability and authority policy.

Current channel boundary:

- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- public website -> Resort Core directly.

Provider configuration is not provider verification.

---

## 15. Observability minimum

Before production approval require:

- API/app logs with timestamps/request context;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup failure alerting;
- HTTP 5xx visibility;
- AuditLog retention appropriate to operations;
- enough evidence to identify the deployed exact commit/image set.

No external monitoring vendor is mandated by current Product Truth.

---

## 16. Controlled production cutover

Only after all P0 gates above are closed:

1. freeze the exact accepted release SHA/images;
2. take a fresh production backup and preserve legacy rollback;
3. re-run host/preflight checks;
4. verify external staging acceptance evidence;
5. reduce/prepare DNS TTL only through an approved controlled change where useful;
6. deploy the exact accepted images/configuration;
7. run readiness/smoke tests before public switch;
8. switch routing/DNS in a controlled window;
9. run `external_public_truth_probe.py` against the public URL;
10. verify public ReservationRequest flow;
11. verify manager login/PMS/chessboard/WSS;
12. verify staff access/tasks;
13. monitor errors/database/containers;
14. keep legacy and database rollback available throughout acceptance.

Final DNS switch is an irreversible/high-impact production action and requires explicit production approval.

---

## 17. Rollback

Application rollback:
- redeploy the previously accepted release/image set.

Database rollback:
- use the rehearsed backup/restore procedure appropriate to the release;
- do not improvise destructive reverse migrations in production.

Public-site/DNS rollback:
- route traffic back to the preserved legacy target when required;
- restore previous DNS records from the captured zone/evidence;
- re-run public smoke checks.

Rollback is not considered available merely because previous code still exists in Git.

---

## 18. Current stop/go status

### GO for repository / CI-local work

Current audited executable head has successful Core, PMS, operations, public-truth, migration, backup/restore, dependency, production-package and full-staging CI contours.

### STOP for production cutover

Production remains blocked because actual host access/preflight, legacy full backup, external HTTPS/WSS staging, physical room truth, real-device acceptance and final cutover evidence are missing.

Do not claim `PRODUCTION READY`, `LIVE`, or `VERIFIED IN PRODUCTION` until those gates have real evidence.
