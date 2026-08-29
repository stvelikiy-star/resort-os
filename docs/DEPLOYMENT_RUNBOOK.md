# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 2.0
Date: 2026-08-29
Status: RELEASE HANDOFF PREPARED / CI-LOCAL STAGING VERIFIED / PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION EXECUTED

This runbook defines the controlled external deployment and cutover procedure. It is **not** evidence that production deployment has happened.

Canonical factual implementation state: `knowledge/04_CURRENT_STATE.md`.

**CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

---

## 1. Current deployment unit

Approved one-server topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16, private to deployment network;
- FastAPI Resort Core (`api`);
- public Next.js site (`web`);
- PMS/admin Next.js application (`admin`);
- staff Next.js PWA (`staff`);
- pinned n8n `2.36.2`;
- persistent PostgreSQL/media/n8n state;
- local backup directory plus off-site copy expected.

Canonical authority remains:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

NFC is outside the active Three Crowns V1 runtime.

---

## 2. Audited executable evidence

Repository: `stvelikiy-star/resort-os`
Branch: `integration/site-pms-cms-20260827`
PR: `#37`

Latest fully audited executable head:

`1be110c35e1e7d5876cae40a1b58cef42bd10a22`

All **26/26 pull-request workflow contours** associated with that exact executable head completed `success`.

Key evidence:

- Resort Core CI `33245328528`;
- Three Crowns Full Staging Gate `33245328535`;
- Single Server Production Package CI `33245328529`;
- Production Migration Baseline CI `33245328548`;
- PostgreSQL Backup Restore CI `33245328550`;
- Dependency Security Inspection `33245328532`;
- PMS Chessboard Mutation CI `33245328512`;
- Realtime PMS CI `33245328538`;
- Guest Services PMS CI `33245328498`;
- Hotel Operations CI `33245328499`;
- Owner Intelligence CI `33245328544`;
- Owner Control V2 CI `33245328508`;
- Owner Growth Control CI `33245328533`;
- Control Center Monorepo Contract CI `33245328536`;
- Unified Inbox CI `33245328518`;
- Payment Idempotency CI `33245328520`;
- Public Site Truth CI `33245328516`;
- AI Administrator CI `33245328564`;
- AI Sales Draft CI `33245328545`;
- n8n Resort Core Contract CI `33245328514`;
- n8n Workflow JSON CI `33245328523`;
- Automation Contract CI `33245328527`;
- Data Intake Integrity CI `33245328525`;
- Staff Voice CI `33245328540`;
- Telegram Sales CI `33245328543`;
- NFC Deferred Scope CI `33245328521`.

Documentation-only commits after this head do not broaden executable verification.

The Actions artifact from the exact-head production-package run was verified as produced by CI at run time, but the GitHub artifact is no longer available for download in the current connector session. Do not substitute an older ZIP and call it the exact-head package.

---

## 3. Business authority boundary

`ReservationRequest != Reservation`.

A human OWNER/MANAGER remains responsible for reservation confirmation and payment fact confirmation.

AI/n8n must not:

- guarantee a Reservation;
- confirm payment;
- invent a fixed prepayment percentage;
- invent QR/payment links/instructions;
- bypass Resort Core availability/pricing;
- write PostgreSQL directly as a generic business interface.

Growth candidates are internal manager work and **not marketing consent**. `outbound_authority = NONE_AUTOMATIC`.

Executive Pack is a read/composition surface only. It does not create Reservation, Payment, GuestEngagement, snapshots or communications.

---

## 4. Verified migration gate

Committed migration chain:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`

Clean `prisma migrate deploy`, exact five-migration ledger, database constraints, 84-room / 12-room-type development seed and migration-aware backup -> clean restore are CI-verified.

Production must use:

```bash
npx prisma migrate deploy
```

Do not use `prisma db push` as the production migration mechanism.

Required production evidence:

- fresh backup before migration;
- exact release SHA/image set recorded;
- migration command/result captured;
- ledger equals all five migrations above;
- readiness/smoke tests pass;
- tested restore path remains available.

---

## 5. Hard production blockers

Production cutover remains **STOP** while any of these are missing:

1. Actual Beget host/account has not passed non-destructive `scripts/host_preflight.sh`.
2. Current live `3korony.com` has no verified full rollback backup in project evidence.
3. Isolated external HTTPS/WSS staging has not been deployed and accepted on the real host/network.
4. External rendered public-truth probe has not passed against real staging.
5. Owner-confirmed physical 84-room production register remains incomplete.
6. Real iPhone/Android/browser/Telegram acceptance remains incomplete.
7. Real launch-enabled provider E2E remains incomplete.
8. Fresh pre-cutover backup/preflight/secrets/DNS rollback evidence remains absent.

No GitHub CI result by itself authorizes production DNS switch or provider activation.

---

## 6. Non-destructive host capability gate

Before installing, stopping, replacing or reconfiguring anything on the purchased host:

```bash
bash scripts/host_preflight.sh
```

Interpretation:

- `RESULT: PASS` — host capability checks passed;
- `RESULT: PASS WITH WARNINGS` — warnings must be reviewed before deployment;
- `RESULT: BLOCKED` — do not deploy this topology to that host.

This is a host capability gate only; it does not prove application correctness over public HTTPS/WSS.

---

## 7. Preserve current live site first

Do not stop or overwrite the legacy site and do not switch DNS until a verified rollback point exists.

Minimum rollback evidence:

- hosting provider/account identified;
- current DNS records captured/exported;
- current web root/app source archived;
- current legacy DB dumped if present;
- uploads/media archived;
- web-server/vhost configuration captured where accessible;
- relevant runtime/config captured;
- backup checksum, size and timestamp recorded;
- restore target/procedure identified;
- rollback owner recorded.

A public HTML crawl alone is **not** a full rollback backup.

---

## 8. External staging deployment sequence

Use an isolated staging hostname. Do **not** point the live apex to the new stack yet.

Sequence:

1. verify legacy rollback backup;
2. run and pass host preflight;
3. prepare production/staging secrets out-of-band;
4. create persistent directories/volumes;
5. start private PostgreSQL;
6. apply all five committed migrations;
7. load only approved/evidence-backed data;
8. bootstrap authorized users out-of-band;
9. build/pull the exact reviewed release;
10. start Caddy + web/admin/staff/Core + n8n as required;
11. keep PostgreSQL private;
12. verify readiness, HTTPS, WSS, cookies, CORS and routing externally.

---

## 9. External acceptance matrix

### Infrastructure

- valid public HTTPS;
- intended HTTP -> HTTPS redirect;
- API readiness healthy;
- real-browser WSS upgrade works;
- PostgreSQL is not publicly exposed;
- persistence survives restart;
- logs accessible;
- backup path writable and monitored.

### Public site

- actual Resort OS site renders, not preview/stub;
- RU/KG/EN works;
- room catalog/content reviewed;
- availability/pricing uses Core;
- booking creates `ReservationRequest`, not automatic Reservation;
- no fixed/unapproved prepayment/acquiring claims;
- no gym or sports-ground claims;
- owner-approved transfer, food, parking, service and rules facts render correctly.

Run:

```bash
python3 scripts/external_public_truth_probe.py https://<staging-host>/
```

### PMS / reception / chessboard

Verify with isolated test dates:

`ReservationRequest -> manager quote -> manager-confirmed payment fact -> Reservation -> chessboard -> check-in -> optional move/Split Stay -> optional Guest Service -> check-out -> housekeeping`.

Also verify:

- stale/conflict rejection;
- realtime browser refresh;
- TECH_BLOCK protection;
- CLEAN check-in gate;
- AuditLog;
- property isolation.

### Guest Services

Verify:

- eligible active Reservation only;
- Reservation-linked service context;
- valid status transitions;
- no automatic accommodation-total mutation;
- no automatic Payment creation.

### Owner Intelligence / Control / Growth / Executive Pack

Verify externally in the real Admin browser:

- Guest history and repeat-Guest fail-closed identity;
- 84-room management heatmap;
- period comparison and exports;
- 7/30-day on-books Owner Control;
- Action Center;
- snapshot-based pickup only when historical data exists;
- Growth post-stay/return queues;
- NPS with visible sample size;
- detractor recovery workflow;
- `outbound_authority = NONE_AUTOMATIC`;
- Executive Pack MTD / 30-day / debt / pickup / NPS / recovery composition;
- browser print/PDF.

### Staff

- MAID/TECHNICIAN RBAC;
- mobile task UI;
- housekeeping inspection/rework/acceptance;
- technician flow;
- real-device acceptance.

### AI / messaging

Website AI:

- real browser/mobile rendering;
- Core-direct availability/pricing;
- no Reservation/payment authority;
- provider-unavailable behavior;
- prompt-injection/adversarial acceptance.

WhatsApp/API Green only if launch-enabled:

- real hotel number;
- secrets stored out-of-band;
- webhook authenticity;
- duplicate webhook/idempotency;
- unavailable-date case;
- prompt-injection case;
- ReservationRequest-only authority.

---

## 10. Owner-approved public truth boundary

Current factual boundary includes:

- booking admin: `+996 558 08 50 02`;
- manager / WhatsApp / Telegram: `+996 558 08 50 08`;
- email: `3koronykg@mail.ru`;
- parking: **approximately 20–30 cars, free for staying guests**;
- winter sauna: 5000 KGS/hour, 4–5 people;
- billiards: 500 KGS/hour;
- table tennis: free;
- no gym/training room;
- no sports grounds/fields;
- New Year pricing remains UNKNOWN until separately approved.

Transfer and food tariffs remain subject to the canonical owner-approved fact set used by the public-truth guards.

Do not publish or reintroduce without new owner-approved evidence:

- fixed 30% prepayment;
- automatic first-night prepayment rule;
- automatic two-day unpaid hold;
- unverified online acquiring;
- unverified Elsom route;
- AI-generated payment QR/link/instructions.

---

## 11. Backup / restore gate

Repository backup/restore implementation is CI-verified, but production needs a fresh real backup.

Record before cutover:

- backup frequency;
- retention;
- encrypted off-site location;
- restore owner;
- restore procedure;
- checksum/size;
- last successful restore-test timestamp.

Never improvise destructive reverse SQL as the primary production rollback strategy.

---

## 12. Security / session gate

Production must use HTTPS and secure cookie configuration.

`CORS_ORIGINS` must contain only approved UI origins.

Use a shared cookie domain only when intentionally required and externally tested.

Frontend visibility is not authorization: RBAC and resource boundaries remain server-side.

Never commit production secrets.

---

## 13. Observability minimum

Before production approval require:

- API/app logs with timestamps/request context;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup failure alerting;
- HTTP 5xx visibility;
- AuditLog retention suitable for operations;
- evidence identifying deployed exact commit/image set.

---

## 14. Controlled production cutover

Only after all P0 gates close:

1. freeze exact accepted release SHA/images;
2. take fresh production backup and preserve legacy rollback;
3. rerun host/preflight checks;
4. confirm external staging acceptance evidence;
5. prepare DNS rollback record;
6. deploy exact accepted images/config;
7. run readiness/smoke tests before public switch;
8. switch routing/DNS in a controlled window after explicit approval;
9. run external public-truth probe against public URL;
10. verify public ReservationRequest flow;
11. verify manager login/PMS/chessboard/Guest Services/Growth/Executive/WSS;
12. verify staff access/tasks;
13. monitor errors/database/containers;
14. keep legacy and DB rollback available throughout acceptance.

Final DNS switch is a high-impact production action and requires explicit owner approval.

---

## 15. Rollback

Application rollback:

- redeploy the previously accepted release/image set.

Database rollback:

- use the rehearsed backup/restore procedure appropriate to the release;
- do not improvise destructive reverse migrations.

Public-site/DNS rollback:

- route traffic back to preserved legacy target;
- restore captured previous DNS records;
- rerun public smoke checks.

Rollback is not considered available merely because previous code exists in Git.

---

## 16. Current GO / STOP status

### GO — repository and delivery demonstration

Exact executable head `1be110c35e1e7d5876cae40a1b58cef42bd10a22` has **26/26 associated PR workflow contours successful**, including Core, PMS, Guest Services, Owner Intelligence, Owner Control V2, Growth Control, Executive Pack build/composition, operations, public truth, five-migration baseline, backup/restore, dependency inspection, single-server package and Full Staging.

### STOP — external production cutover

Production remains blocked by real external evidence: Beget host preflight, full rollback backup of current live site, external HTTPS/WSS staging, owner-confirmed physical room truth, real-device/provider acceptance and fresh cutover evidence.

Do not claim `PRODUCTION READY`, `LIVE`, or `VERIFIED IN PRODUCTION` until those gates have real evidence.
