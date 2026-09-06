# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-07**

Use these sources, in order, for current release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary.
2. `knowledge/04_CURRENT_STATE.md` — factual implemented state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — external acceptance and cutover gates.
4. `docs/DEPLOYMENT_RUNBOOK.md` — controlled deployment procedure.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — migration/constraint ledger.
6. `docs/RELEASE_0.62.0_2026-09-07.md` — current release record.

If a dated historical document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.62.0**.  
Accepted executable head: `609a309c97f30b5f95828956188507fc35ed3d0d`.  
Observed tree-equivalent main merge: `bccc491ea24c94668ef1bea4d86fb61a5b8e6f3d`.  
Production source branch: `main`.

Accepted PR #122 head passed **21/21 workflows**. The observed merge retained the same tree and produced **20 eligible successful product/security/migration/staging workflows**; `Release RC Truth CI` failed closed because the previous manifest still described 0.61.0, which this 0.62.0 refreeze corrects.

## Property/database authority

Canonical property truth remains **84 rooms / 12 categories / 48 rates**. Rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

Frozen database boundary remains **22 committed migrations / 87 critical domain constraints**. External staging/production uses `npx prisma migrate deploy`, never `prisma db push` as release evidence.

## Product authority boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation/payment authority.
- AI/n8n do not confirm payment or guarantee reservations.
- Kitchen/Dining totals do not automatically create Hotel Payments.
- Room QR/PIN is not a physical lock credential.
- Real bank acquiring and TTLock remain provider/hardware gated.
- NFC acquiring/wallet remains deferred outside active V1.
- Google Drive/Sheets are control/archive/mirror surfaces, not transaction truth.

## Historical documents

`docs/RELEASE_0.61.0_2026-09-06.md`, `docs/RELEASE_0.60.0_2026-09-05.md`, older staging/handoff/RC documents and historical Vercel previews remain evidence/reference only and must not override the current manifest.

## External production remains fail-closed

Repository green does not mean live production. Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until the launch gate verifies branch protection, Drive permissions, target host/staging, rollback, real devices/providers, monitoring, backup/restore/off-site copy, DNS rollback and explicit owner GO.
