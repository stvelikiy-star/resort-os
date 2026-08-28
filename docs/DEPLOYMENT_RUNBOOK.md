# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Date: 2026-08-29
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

Latest fully audited executable/package head before documentation-only synchronization:

`7eaf9b56579a35c8623b56b3511bc790441fefa0`.

All 23 pull-request-triggered workflow contours associated with that head completed `success`.

Key deployment/release evidence:
- Resort Core CI `33199405433`;
- Three Crowns Full Staging Gate `33199405342`;
- Single Server Production Package CI `33199405351`;
- Dependency Security Inspection `33199405451`;
- Production Migration Baseline CI `33199405463`;
- PostgreSQL Backup Restore CI `33199405368`;
- PMS Chessboard Mutation CI `33199405473`;
- Realtime PMS CI `33199405372`;
- Guest Services PMS CI `33199405441`;
- Hotel Operations CI `33199405399`;
- Public Site Truth CI `33199405465`;
- AI Administrator CI `33199405450`.

Do not convert CI evidence into a claim that the purchased host, external TLS/WSS, live providers, real devices or production DNS are verified.

---

## 3. Required external production inputs

Before external deployment obtain only real infrastructure/configuration values:

- access to the purchased deployment host;
- host type/capability evidence from `scripts/host_preflight.sh`;
- final public/admin/staff/API hostnames and DNS control;
- PostgreSQL production credentials/storage paths;
- production HTTPS/TLS routing;
- owner bootstrap credentials delivered out-of-band and removed/rotated after bootstrap;
- long random n8n/Resort Core service secret;
- real OpenAI/API Green credentials only if those provider contours are explicitly launch-enabled;
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

Resolved repository/CI gates:

- committed production migration chain exists (`0_init`, `1_site_content`, `2_guest_service_tasks`);
- clean `prisma migrate deploy` is CI-verified;
- structured guest-service migration/API/PMS flow is CI-verified;
- migration-aware backup -> clean restore is CI-verified;
- repository-local public truth, owner guest-facts and i18n guards are active;
- CI-local Docker staging is verified;
- current single-server package is verified in CI.

---

## 5. Non-destructive host capability gate

Before installing, stopping, replacing or reconfiguring anything on the purchased host, run:

```bash
bash scripts/host_preflight.sh
```

The script is intentionally non-destructive. It checks Linux/architecture, CPU, RAM, disk, root/sudo, Docker/Compose, outbound registry connectivity, listeners on 80/443, host-level 5432 exposure, persistent target-path access and existing web services.

Interpretation:

- `RESULT: PASS` — infrastructure checks passed;
- `RESULT: PASS WITH WARNINGS` — understand/accept warnings before cutover;
- `RESULT: BLOCKED` — do not deploy this topology to that host.

Host preflight does not prove external staging or production correctness.

---

## 6. Preserve the current legacy site before deployment

The currently live site remains a rollback dependency until the new system passes external acceptance.

Do not stop its web service, overwrite its document root, replace its database or switch DNS before a verified rollback point exists.

Because the actual hosting type/filesystem/control panel are currently UNKNOWN, do not invent backup commands or paths.

Minimum evidence required:
- hosting provider/account identified;
- current DNS zone exported or recorded;
- current web root/app source archived;
- current legacy database dumped if one exists;
- uploads/media archived;
- current web-server/vhost configuration captured where accessible;
- relevant runtime/config values captured;
- backup checksum/size/timestamp recorded;
- restore target/procedure identified;
- rollback owner and maximum acceptable cutover window recorded.

A public HTML crawl alone is **not** a full rollback backup.

If the purchased host is shared hosting and cannot support the approved Docker topology, preserve it as rollback and deploy Resort OS to a separate suitable VPS/VDS.

---

## 7. Production migration gate

Current committed migration chain:

- `0_init`;
- `1_site_content`;
- `2_guest_service_tasks`.

`2_guest_service_tasks` adds structured reservation-linked guest-service context on `operational_tasks` while preserving legacy nullable tasks.

Do not use `prisma db push` as the production migration mechanism.

Production procedure must use the committed migration chain:

```bash
npx prisma migrate deploy
```

Required production evidence:
- backup taken before migration;
- exact reviewed release SHA/image set recorded;
- migration command/result captured;
- migration ledger equals `0_init,1_site_content,2_guest_service_tasks`;
- required critical constraints and guest-service columns/checks verified;
- application readiness/smoke checks passed;
- rollback/restore path remains available.

CI evidence proves the migration process in clean/isolated environments; it does not prove the production database has been migrated.

---

## 8. Backup / restore gate

Repository backup/restore implementation has CI evidence, but production still needs a fresh real backup.

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

Use an isolated hostname/subdomain or routing that does not replace the live apex site.

Do not point `3korony.com` apex traffic to the new stack at this stage.

Sequence:
1. preserve legacy rollback evidence;
2. pass `scripts/host_preflight.sh`;
3. prepare host-only environment values with no secrets committed to Git;
4. create persistent directories/volumes;
5. start private PostgreSQL;
6. apply all three committed migrations;
7. load only evidence-backed staging/test data or an approved production import;
8. bootstrap authorized users out-of-band;
9. build/pull exact reviewed release images;
10. start Caddy + web/admin/staff/Core + n8n as required;
11. keep PostgreSQL private;
12. verify HTTPS/WSS, cookies, CORS, routing and health endpoints from outside the host.

Do not use an old preview/stub as a substitute for this gate.

---

## 10. External staging acceptance

### Infrastructure
- valid public HTTPS;
- intended HTTP -> HTTPS redirect;
- healthy API readiness;
- real-browser WSS upgrade;
- PostgreSQL not publicly exposed;
- acceptable restart/persistence behavior;
- accessible logs;
- writable/monitored backup path.

### Public site
- real Resort OS site renders, not a preview stub;
- RU/KG/EN works;
- room catalog/content reviewed;
- availability/pricing uses Core;
- booking creates `ReservationRequest`, not automatic confirmed Reservation;
- no stale automatic prepayment/payment-provider claims;
- no rejected gym/sports-ground claims;
- owner-approved transfer/food/parking/service/rules facts render correctly.

Run:

```bash
python3 scripts/external_public_truth_probe.py https://<staging-host>/
```

A PASS verifies only the checked rendered response/URL. It does not prove all business flows.

### PMS / reservation lifecycle
Use isolated test data/dates and verify:

`ReservationRequest -> manager quote -> manager-confirmed payment fact -> Reservation -> chessboard -> check-in -> optional move/Split Stay -> optional Guest Service -> check-out -> housekeeping`.

Also verify stale/conflict protection and realtime refresh from the real browser.

Guest Service acceptance must prove:
- only active eligible Reservations can receive structured requests;
- service is linked to Reservation;
- status transitions work;
- no automatic change to accommodation total or Payment occurs;
- property isolation remains enforced.

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
- prompt-injection/adversarial acceptance.

WhatsApp/API Green, only if launch-enabled:
- real hotel number;
- provider credentials stored as secrets;
- webhook authenticity/secret handling;
- duplicate webhook/idempotency;
- unavailable-date case;
- prompt-injection case;
- ReservationRequest-only authority.

---

## 11. PMS / chessboard acceptance boundary

The current canonical V9 chessboard is not a presentation-only grid. Repository CI covers move/resize/Split Stay, stale conflict rejection, history preservation, housekeeping consequences, realtime and AuditLog.

Structured Guest Services are integrated into the same PMS composition and remain Resort Core authoritative.

External acceptance must prove those behaviors over the actual HTTPS/WSS network and real Admin browser.

Do not replace the canonical chessboard with a parallel scheduling source of truth. Review/demo packaging is presentation only unless backed by the same Core APIs.

---

## 12. Public payment / sales truth boundary

Do not publish or reintroduce without new owner-approved evidence:
- fixed 30% prepayment;
- automatic first-night prepayment rule;
- automatic two-day unpaid-hold rule;
- unverified online-card acquiring;
- unverified Elsom payment route;
- AI-generated payment links/QR/payment instructions.

Manager remains responsible for current V1 payment amount/terms/method and factual payment confirmation.

The repository public-truth guards fail closed on current stale/unapproved patterns.

---

## 13. Owner-approved guest fact boundary

Current public release truth includes the owner-approved transfer tariffs, retained current food pricing baseline, free parking capacity 30–50 vehicles, winter sauna 5000 KGS/hour for 4–5 people, billiards 500 KGS/hour, free table tennis, excursion manager confirmation/update wording, walking-distance thermal springs and independent seasonal beach water operators.

The hotel does **not** currently have a gym/training room or sports grounds/fields. Do not restore those legacy claims.

New Year pricing remains UNKNOWN until separately approved.

---

## 14. Cookie / CORS / authorization gate

Production must use HTTPS and secure cookie configuration.

`CORS_ORIGINS` must contain only approved UI origins.

Set a shared cookie domain only when intentionally required and externally tested.

Frontend visibility is not authorization. All role/resource mutation boundaries remain server-side.

External staging must prove cross-origin/session behavior from real browsers before cutover.

---

## 15. n8n / AI authority boundary

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

## 16. Observability minimum

Before production approval require:
- API/app logs with timestamps/request context;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup failure alerting;
- HTTP 5xx visibility;
- AuditLog retention appropriate to operations;
- evidence identifying the deployed exact commit/image set.

No external monitoring vendor is mandated by current Product Truth.

---

## 17. Controlled production cutover

Only after all P0 gates are closed:
1. freeze exact accepted release SHA/images;
2. take fresh production backup and preserve legacy rollback;
3. re-run host/preflight checks;
4. verify external staging acceptance evidence;
5. prepare DNS TTL only through an approved controlled change where useful;
6. deploy exact accepted images/configuration;
7. run readiness/smoke tests before public switch;
8. switch routing/DNS in a controlled window;
9. run `external_public_truth_probe.py` against public URL;
10. verify public ReservationRequest flow;
11. verify manager login/PMS/chessboard/Guest Services/WSS;
12. verify staff access/tasks;
13. monitor errors/database/containers;
14. keep legacy and database rollback available throughout acceptance.

Final DNS switch is an irreversible/high-impact production action and requires explicit production approval.

---

## 18. Rollback

Application rollback:
- redeploy the previously accepted release/image set.

Database rollback:
- use the rehearsed backup/restore procedure appropriate to the release;
- do not improvise destructive reverse migrations in production.

Public-site/DNS rollback:
- route traffic back to preserved legacy target when required;
- restore previous DNS records from captured evidence;
- re-run public smoke checks.

Rollback is not considered available merely because previous code exists in Git.

---

## 19. Current stop/go status

### GO for repository / CI-local work

Audited executable head `7eaf9b56579a35c8623b56b3511bc790441fefa0` has all 23 associated PR-triggered workflows successful, including Core, PMS, Guest Services, operations, public truth, three-migration baseline, backup/restore, dependency inspection, single-server package and Full Staging.

### STOP for production cutover

Production remains blocked because actual host access/preflight, verified legacy full backup, external HTTPS/WSS staging, owner-confirmed physical room truth, real-device acceptance and final cutover evidence are missing.

Do not claim `PRODUCTION READY`, `LIVE`, or `VERIFIED IN PRODUCTION` until those gates have real evidence.
