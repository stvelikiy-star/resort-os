# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-07**

Use these sources, in order, for current release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary.
2. `knowledge/04_CURRENT_STATE.md` — factual implemented state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — external acceptance and cutover gates.
4. `docs/DEPLOYMENT_RUNBOOK.md` — controlled deployment procedure.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — migration/constraint ledger.
6. `docs/RELEASE_0.62.2_2026-09-07.md` — current release record.

If a dated historical document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.62.2**.  
Accepted executable head: `b79e22ee56c43e5f9146df7597d4c9e5e4124afa`.  
Observed tree-equivalent main merge: `731e81c2d2a4ccc91fae319b73f0d4b8eb9979b5`.  
Production source branch: `main`.

Accepted PR #127 head passed **41/41 workflows**. The observed merge retained the same tree and produced **32/32 eligible successful product/security/migration/staging workflows**; `Release RC Truth CI` failed closed because the previous 0.62.1 manifest correctly detected executable route-hardening drift. This 0.62.2 refreeze is the controlled correction.

## 0.62.2 hardening delta

- Kitchen menu mutation authority no longer depends on router registration order.
- Legacy operational bootstrap/PATCH menu mutations are removed from the active application graph before composition.
- Runtime active API route uniqueness is a Release Gate invariant.
- Active FastAPI/OpenAPI version identity is 0.62.2.
- Existing 0.62.1 Admin demo and Kitchen production fail-close hardening remains active.
- Public website source remained frozen: PR #127 changed zero `apps/web/**` files.

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

## Current owner plan

GitHub branch protection and Google Drive permission hardening are advisory/deferred rather than current internal-RC blockers. Beget/VPS is intentionally the final phase.

## External production remains fail-closed

Repository green does not mean live production. Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until real target-host, rollback, HTTPS/WSS staging, device/provider, monitoring, backup/restore/off-site, DNS rollback and explicit owner GO evidence exists.

Historical release files including 0.62.1 and earlier remain reference evidence only and do not override the current 0.62.2 manifest.
