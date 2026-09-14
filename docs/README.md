# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-14**

Use these sources, in order, for current release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary.
2. `knowledge/04_CURRENT_STATE.md` — factual implemented state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — external acceptance and cutover gates.
4. `docs/DEPLOYMENT_RUNBOOK.md` — controlled deployment procedure.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — migration/constraint ledger.
6. `docs/RELEASE_0.62.2_2026-09-07.md` — current same-version release/refreeze record.

If a dated historical document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.62.2**.  
Accepted executable head: `7ae394bbb549bb6200c84e9c46d47ed5cd45499a`.  
Observed tree-equivalent main merge: `b13bacad3f2e923f51354b1839371d07179b2e8c`.  
Production source branch: `main`.

Accepted PR #157 head passed **52/52 workflows** with zero failures. The observed merge retained the same tree. Its first push produced **37/39 successful workflows**; `Release RC Truth CI` and `Launch Acceptance CI` correctly failed closed against the older 2026-09-07 frozen manifest. The 2026-09-14 same-version refreeze is the controlled correction.

## Current product delta

- Marketing remains part of final Admin/Core and includes consent/attribution and automation contracts.
- Agent CRM/reporting and Reception agent filtering are active in the accepted contour.
- Dated maintenance/manual room holds are part of Reception operations.
- Extra-bed restrictions are enforced in Resort Core for the three owner-approved denied room categories.
- Returning guests with a prior completed stay receive the automatic 10% accommodation discount; alternative discounts remain auditable.
- Booking schedule drag/drop remains preview + explicit confirmation before commit.
- Public booking-request success remains server-confirmed.
- Existing security, Kitchen/Dining, Guest OS, realtime, backup/restore and release hardening remains active.

## Property/database authority

Canonical property truth remains **84 rooms / 12 categories / 48 rates**. Rooms 501/502 remain owner-approved two-person basement inventory above the laundry.

Frozen database boundary is **24 committed migrations / 93 critical domain constraints**, ending with:
- `z99_marketing_consent_attribution_20260912`;
- `zz100_owner_ops_corrections_20260914`.

External staging/production uses `npx prisma migrate deploy`, never `prisma db push` as release evidence.

## Full Test evidence

Railway `Three Crowns Full Test` has API/Web/Admin/Staff deployed from merge SHA `b13bacad3f2e923f51354b1839371d07179b2e8c`; all four latest deployments are successful. API applied the full 24-migration chain and passed readiness. This is integration evidence, not real production cutover evidence.

## Product authority boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation/payment authority.
- AI/n8n do not confirm payment or guarantee reservations.
- Kitchen/Dining totals do not automatically create Hotel Payments.
- Room QR/PIN is not a physical lock credential.
- Real bank/MKassa/TTLock remain provider/hardware gated.
- NFC acquiring/wallet remains deferred outside active V1.
- Google Drive/Sheets are control/archive/mirror surfaces, not transaction truth.

## External production remains fail-closed

Repository and Full Test green do not mean live production. Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until real target-host, branch-protection/permissions, rollback, HTTPS/WSS, device/provider, monitoring, backup/restore/off-site, immutable deployment linkage, DNS rollback and explicit owner GO evidence exists.

Historical release files remain reference evidence only and do not override the current machine manifest and canonical state documents.
