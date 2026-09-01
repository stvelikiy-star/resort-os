# THREE CROWNS RESORT OS — DEPLOYMENT RUNBOOK

Version: 3.0
Date: 2026-09-01
Status: RELEASE-CANDIDATE HANDOFF / CI-LOCAL VERIFIED / EXTERNAL CUTOVER STOP

This runbook defines controlled external deployment and cutover. It is **not evidence that production deployment has happened**.

Canonical implementation state: `knowledge/04_CURRENT_STATE.md`.
Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md`.

**CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

---

## 1. Current release boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Integration head after Block 11 merge: `91699f70f774726eb61a9882ccbdfe5944471856`.
Audited feature head: `7e8193447fc09dff2c375b5aa63ce4573e8210a8`.

The audited feature head completed **37/37 pull-request workflow contours successfully** before merge. The merge commit contains the reviewed tree but does not itself constitute external acceptance.

Key verified contours include:

- Resort Core;
- Full Staging Gate;
- Single Server Production Package;
- Production Migration Baseline;
- PostgreSQL Backup Restore;
- Dependency Security Inspection;
- PMS Owner Grid and PMS Chessboard Mutation;
- Realtime PMS;
- Reception RBAC;
- Guest OS Core / Access / Requests;
- Guest CRM;
- Guest Services Center;
- Finance Control;
- Owner Intelligence / Control V2 / Growth / Dashboard Analytics;
- Public Site Truth and Public Browser Acceptance;
- Unified Inbox / AI Unified Communications / AI Sales / AI Administrator;
- n8n Resort Core and Automation contracts;
- Staff Voice / Hotel Operations;
- Service Point QR;
- NFC Deferred Scope.

---

## 2. Deployment topology

Approved V1 topology:

- Caddy HTTPS/WSS edge;
- PostgreSQL 16 private to deployment network;
- FastAPI Resort Core;
- public Next.js site;
- Resort OS admin/PMS;
- staff PWA;
- pinned n8n runtime when automation is enabled;
- persistent PostgreSQL/media/n8n state;
- local backup directory plus off-site copy.

Canonical authority:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`.

NFC acquiring/wallet remains outside active V1 runtime.

---

## 3. Database release contract

Committed migration chain:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`

Production migration mechanism:

```bash
npx prisma migrate deploy
```

Do **not** use `prisma db push` for production migration.

Current critical PostgreSQL domain fingerprint: **27 constraints**, defined canonically in `scripts/release_contract.py`.

Production evidence must capture:

- exact release SHA/image set;
- backup before migration;
- migration command/result;
- exact seven-migration ledger;
- readiness/smoke result;
- tested restore path.

---

## 4. Business authority boundary

`ReservationRequest != Reservation`.

Human OWNER/MANAGER retains reservation confirmation and payment fact authority.

AI/n8n must not:

- guarantee a Reservation;
- confirm payment;
- invent a fixed prepayment percentage;
- invent payment QR/link/instructions;
- bypass Core availability/pricing;
- write PostgreSQL directly as a generic business interface.

Growth outbound authority remains `NONE_AUTOMATIC`.

---

## 5. Hard external production blockers

Production cutover remains **STOP** while any required evidence is missing:

1. owner-approved physical 84-room production register;
2. actual Beget host/account non-destructive preflight;
3. verified full rollback backup of currently live `3korony.com` target;
4. isolated external HTTPS/WSS staging on real infrastructure;
5. external public-truth probe against that staging;
6. real iPhone/Android/desktop/Telegram/staff acceptance;
7. real provider E2E for every provider enabled at launch;
8. real monitoring/alerting evidence;
9. fresh pre-cutover backup evidence;
10. exact DNS rollback capture;
11. explicit final owner cutover approval.

The 84-room development seed is not owner approval of the physical production register.

No GitHub CI result by itself authorizes production DNS switch or provider activation.

---

## 6. Fail-closed launch evidence

Template:

`release/launch-evidence.example.json`

Repository verifier:

```bash
python scripts/verify_launch_acceptance.py --mode repository
```

Final structural cutover verifier after real evidence is collected outside secrets storage:

```bash
python scripts/verify_launch_acceptance.py \
  --mode cutover \
  --manifest /secure/path/launch-evidence.json \
  --release-sha <exact-accepted-release-sha>
```

The verifier validates supplied evidence metadata. It does not manufacture or independently observe external evidence.

---

## 7. Non-destructive host gate

Before installing, stopping, replacing or reconfiguring anything on the actual target host:

```bash
bash scripts/host_preflight.sh
```

Interpretation:

- `RESULT: PASS` — host capability checks passed;
- `RESULT: PASS WITH WARNINGS` — warnings require review;
- `RESULT: BLOCKED` — stop deployment.

Host capability does not prove application correctness over public HTTPS/WSS.

---

## 8. Preserve the current live site first

Do not overwrite the existing public target and do not switch DNS until rollback evidence exists.

Minimum rollback package:

- provider/account identified;
- current DNS records captured;
- current web root/app source archived;
- current legacy DB dumped if applicable;
- uploads/media archived;
- web-server/vhost config captured where accessible;
- runtime/config captured where applicable;
- backup checksum, size and timestamp recorded;
- restore target/procedure identified;
- rollback owner recorded.

A public HTML crawl is not a full rollback backup.

---

## 9. External staging deployment

Use an isolated staging hostname. Do not point the live apex to the new stack.

Sequence:

1. verify legacy rollback package;
2. run actual-host preflight;
3. prepare secrets out-of-band;
4. provision persistent storage/volumes;
5. start private PostgreSQL;
6. apply all seven committed migrations;
7. load only approved/evidence-backed production data;
8. bootstrap authorized users out-of-band;
9. build/pull the exact accepted release;
10. start Caddy + web/admin/staff/Core + n8n as required;
11. keep PostgreSQL private;
12. verify readiness, HTTPS, WSS, cookies, CORS and persistence externally.

---

## 10. External acceptance matrix

### Infrastructure

Verify:

- valid public HTTPS;
- intended HTTP -> HTTPS redirect;
- API readiness;
- real-browser WSS upgrade;
- PostgreSQL not publicly exposed;
- persistence survives restart;
- logs accessible;
- backup path writable;
- monitoring/alerting active.

### Public site

Verify real rendered RU/KG/EN pages, rooms, approved facts, availability/pricing through Core and `ReservationRequest` creation without automatic Reservation/Payment confirmation.

Run:

```bash
python3 scripts/external_public_truth_probe.py https://<staging-host>/
```

### PMS / Reception

Verify with isolated dates:

`ReservationRequest -> manager decision/payment fact -> Reservation -> chessboard -> check-in -> optional move/Split Stay -> optional Guest Service -> check-out -> housekeeping`.

Also verify stale/conflict rejection, realtime, TECH_BLOCK, CLEAN check-in gate, AuditLog and Reception RBAC.

### Guest OS / CRM

Verify:

- Room QR resolve;
- PIN/session on real device;
- Guest request -> staff -> DONE -> My Requests;
- relocation changes factual RoomAssignment;
- checkout revokes GuestSession;
- repeated Guest history remains one fail-closed identity.

### Service Point QR

Verify at least one real printed/displayed common-area QR:

`scan -> safe point metadata -> anonymous request -> correct OperationalTask role -> DONE`.

Verify old QR after rotation/revoke no longer resolves. This QR must not expose Guest/Reservation/Payment data and must not activate NFC.

### Finance / Owner

Verify debt/paid facts, checked-out debt, timezone boundary, owner dashboards, Action Center, history, Growth/NPS sample size and no fabricated forecast/automatic outbound authority.

### Staff

Verify MAID/TECHNICIAN mobile flows, Reception role, housekeeping inspection/rework and technician flow on real devices.

### AI / messaging

Website remains direct-Core for booking. Messaging providers, if launch-enabled, must prove real webhook authenticity, duplicate/idempotency handling, provider delivery evidence, unavailable-date behavior and ReservationRequest-only authority.

If a provider is disabled at launch, mark it `NOT_REQUIRED`; do not simulate provider success.

---

## 11. Production preflight

Production environment must pass `scripts/production_preflight.py` with actual secrets/env and database. Important checks include:

- `APP_ENV=production`;
- secure cookies;
- exact HTTPS CORS origins;
- no test/bootstrap passwords;
- production automation service key when required;
- exact migrations/critical constraints;
- unique physical room codes;
- rates loaded;
- recent verified backup marker.

A synthetic CI pass of Beget hardening does not replace actual-host evidence.

---

## 12. Observability minimum

Before production approval require real evidence for:

- API/app logs with timestamps/request context;
- container restart visibility;
- health/readiness monitoring;
- PostgreSQL disk/storage monitoring;
- backup-failure alerting;
- HTTP 5xx visibility;
- AuditLog retention;
- exact deployed commit/image identification.

---

## 13. Controlled cutover

Only after every required launch-evidence gate is VERIFIED:

1. freeze accepted release SHA/images;
2. take fresh pre-cutover backup;
3. verify legacy rollback and DNS rollback target;
4. rerun host and production preflight;
5. confirm external staging/device/provider evidence;
6. obtain explicit owner approval;
7. deploy exact accepted release;
8. run readiness/smoke before public switch;
9. switch DNS/routing in controlled window;
10. run external public-truth and booking smoke;
11. verify PMS/Guest OS/Staff/WSS;
12. monitor errors/database/containers;
13. roll back if acceptance criteria fail.

Final DNS switch is a high-impact production action and requires explicit owner approval.

---

## 14. Rollback

Application rollback: redeploy the previously accepted image/release.

Database rollback: use rehearsed backup/restore; do not improvise destructive reverse SQL.

Public/DNS rollback: restore captured previous DNS/routing and rerun public smoke checks.

Rollback is not available merely because older code exists in Git.

---

## 15. Current GO / STOP

### GO — repository release-candidate engineering

Current repository has a reviewed Block 11 tree with 37/37 PR workflow contours successful and a verified seven-migration/27-constraint release contract.

### STOP — external production cutover

Production remains blocked by external evidence listed in section 5. Do not claim `PRODUCTION READY`, `LIVE` or `VERIFIED IN PRODUCTION` until those gates are supported by real evidence and the owner explicitly authorizes cutover.
