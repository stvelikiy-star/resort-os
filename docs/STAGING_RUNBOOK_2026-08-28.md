# Three Crowns Resort OS — Staging Runbook (2026-08-28 reference)

Status: **HISTORICAL LOCAL-STAGING REFERENCE / SUPERSEDED FOR EXTERNAL RELEASE**  
Reviewed: **2026-09-02**

> Do not use this dated file as release authority. Current external staging/cutover authority is `release/current-rc.json`, `knowledge/04_CURRENT_STATE.md`, `knowledge/09_LAUNCH_ACCEPTANCE.md`, `docs/DEPLOYMENT_RUNBOOK.md`, and GitHub launch board #39.

The original 2026-08-28 runbook was useful for building a disposable localhost staging stack. Since then, the room register, migration ledger, Guest OS, Service Point QR, Kitchen and release-gate architecture have advanced. The old claims that the 84-room register still awaited owner confirmation and that a Google room sheet would later become production authority are **superseded**.

## 1. What remains valid from the original local staging mechanics

A disposable local stack may still use isolated loopback ports such as:

- PostgreSQL: `127.0.0.1:15432`;
- Resort Core: `127.0.0.1:18000`;
- public web: `127.0.0.1:13000`;
- admin/PMS: `127.0.0.1:13001`;
- staff PWA: `127.0.0.1:13002`.

Local/disposable staging must:

1. use a separate test database/volume;
2. never reuse production provider credentials;
3. never copy synthetic test data to production;
4. keep Google Sheets as mirror/control only;
5. run the canonical staging acceptance scripts rather than treating a rendered UI as proof;
6. keep NFC acquiring/wallet absent from active V1 runtime.

`prisma db push` may be used only for an explicitly disposable local mechanics test. It is **not** acceptable external release evidence.

## 2. Current source checkout rule

Use the canonical integration branch or an explicitly accepted successor, and record the exact SHA:

```bash
git fetch origin
git checkout integration/site-pms-cms-20260827
git pull --ff-only
git rev-parse HEAD
```

Before any external acceptance, the exact checkout SHA must match the accepted release boundary and deployed application image revision labels. Stale `main` is not a production source.

## 3. Current room-register rule

The canonical room authority is already repository-controlled:

- `data-intake/rooms.csv` — exact 84-room / 12-category target;
- `data-intake/room-register-owner-approval.json` — checksum-bound `OWNER_APPROVED` evidence;
- `data-intake/owner-room-checklist.json` — historical provenance only.

Do **not** collect the room questionnaire again and do not promote an old Google import/sheet into a second mutable production authority.

For a real staging/target database the remaining task is:

```text
canonical register -> dry-run -> exact diff review -> safe apply -> zero diff
```

Use the current physical-room import/reconciliation tooling and preserve runtime state protections. Active guaranteed/check-in facts must not be overwritten by a metadata reconciliation.

## 4. Current migration rule

The release ledger is exactly eight migrations:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`

External staging and production must use:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
cd ../..
```

The target `_prisma_migrations` ledger must match the committed eight-migration sequence exactly. `scripts/production_preflight.py` and the shared `scripts/release_contract.py` enforce this fail-closed contract.

## 5. Local disposable acceptance

For a localhost-only mechanics test, environment may use loopback URLs and test-only credentials. Start isolated PostgreSQL/Core/UI services and run:

```bash
export CORE_API_URL=http://127.0.0.1:18000
export CORE_WS_URL=ws://127.0.0.1:18000
python scripts/staging_acceptance.py
```

The current acceptance contour covers Core readiness, canonical inventory, CMS/runtime truth, availability, `ReservationRequest` boundary, PMS/realtime, staff operations and audited room-state transitions. Newer domain-specific CI additionally covers Guest OS, Service Point QR, Kitchen, finance, AI/inbox and release safety.

A localhost pass proves application mechanics only. It does **not** prove external HTTPS/WSS, provider delivery, mobile devices, backup/restore, monitoring or production networking.

## 6. External HTTPS/WSS staging — current mandatory sequence

Do not infer external acceptance from this historical file. Follow `docs/DEPLOYMENT_RUNBOOK.md` and `knowledge/09_LAUNCH_ACCEPTANCE.md`.

At minimum the real external sequence is:

1. verify the legacy rollback package first;
2. verify the exact accepted SHA and clean checkout;
3. provision isolated staging storage/database/secrets;
4. apply the exact eight migrations with `prisma migrate deploy`;
5. reconcile the canonical 84-room register against the staging target;
6. build/deploy the exact accepted SHA;
7. verify deployed image revision labels;
8. verify HTTPS, WSS, cookies, CORS, persistence and private DB topology;
9. run `scripts/external_staging_acceptance.py` and retain its checksum-backed evidence directory;
10. run real-device acceptance;
11. run E2E only for messaging/payment providers actually intended to be enabled at launch;
12. verify real monitoring, backup age, off-site copy and restore evidence.

The external acceptance runner deliberately refuses non-staging hostnames and does not switch production DNS.

## 7. Realtime / device acceptance

For external staging, verify at minimum:

- iPhone Safari;
- Android Chrome;
- desktop browser;
- Telegram Mini App on supported devices;
- PMS realtime `live` state and reconnect;
- Staff MAID/TECHNICIAN flows;
- Kitchen Admin/DINING_STAFF flow;
- no horizontal/mobile layout breakage in required operational surfaces.

REST success does not prove WSS/session behaviour.

## 8. Provider rule

Provider templates and credentials are separate from Core truth.

- Instagram: provider/ManyChat -> n8n -> Core unified inbox;
- WhatsApp: provider/API Green -> n8n -> Core unified inbox;
- Telegram: controlled direct adapter or n8n path;
- website booking: public website -> Resort Core directly.

n8n/AI may qualify and create a `ReservationRequest`; it must not confirm payment, create guaranteed Reservation, invent a payment route, or write PostgreSQL directly.

Provider `SENT`/`DELIVERED` evidence must come back from the provider path. A timeout/UNKNOWN/QUEUED state is not delivery success.

## 9. Vercel role

Vercel review deployments are DEMO/REVIEW only unless separately accepted under the current release process. A Vercel project/deployment target named `production` does not make it production `3korony.com`.

Historical `three-crowns-v3-preview` / `three-crowns-full-current` surfaces must not override the canonical integration RC. Review deployments should remain `noindex` and should be rebuilt from the canonical RC/successor when a new owner review is needed.

## 10. Current production STOP gates

Production cutover remains blocked until required evidence is real and current, including:

- GitHub branch protection/required checks;
- Drive launch-control permissions no longer exposing public writer access;
- target room reconciliation to zero diff;
- actual host/account preflight;
- verified legacy rollback package;
- isolated external HTTPS/WSS staging acceptance;
- real-device acceptance;
- E2E for providers enabled at launch;
- monitoring/alerting, backup/off-site/restore evidence;
- fresh pre-cutover backup;
- exact DNS rollback capture;
- explicit OWNER GO.

Do not claim `LIVE`, `PRODUCTION READY` or `EXTERNAL VERIFIED` from this local/historical runbook, CI, a Vercel preview, or a template.
