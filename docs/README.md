# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-07**

Use these sources, in order, for current release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary.
2. `knowledge/04_CURRENT_STATE.md` — factual implemented state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — external acceptance and cutover gates.
4. `docs/DEPLOYMENT_RUNBOOK.md` — controlled deployment procedure.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — migration/constraint ledger.
6. `docs/RELEASE_0.62.1_2026-09-07.md` — current release record.

If a dated historical document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.62.1**.  
Accepted executable head: `b3bb0c1be4c522d765509796ddd1d32e8606dc89`.  
Observed tree-equivalent main merge: `7f689458b2cf507d76a8c54fbe164e9492f79aca`.  
Production source branch: `main`.

Accepted PR #125 head passed **28/28 workflows**. The observed merge retained the same tree and produced **23 eligible successful product/security/migration/staging workflows**; `Release RC Truth CI` failed closed because the previous 0.62.0 manifest correctly detected executable hardening drift. This 0.62.1 refreeze is the controlled correction.

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
- Historical `/admin/demo` is fail-closed.
- Kitchen draft bootstrap is unavailable to DINING_STAFF and fail-closed in production.

## Historical documents

`docs/RELEASE_0.62.0_2026-09-07.md`, `docs/RELEASE_0.61.0_2026-09-06.md`, `docs/RELEASE_0.60.0_2026-09-05.md`, older staging/handoff/RC documents and historical Vercel previews remain evidence/reference only and must not override the current manifest.

## External production remains fail-closed

Per owner plan, GitHub branch protection and Drive permission hardening are recommendations/deferred controls; Beget/VPS is the final external phase. Repository green does not mean live production. Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until actual host/staging/rollback/device/provider/monitoring/backup/DNS evidence and explicit owner GO exist.
