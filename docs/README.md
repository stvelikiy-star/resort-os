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
Accepted executable head: `61bd40d7592e842a4d52cfb343483065afb378cb`.  
Observed main merge: `94c849a0833079627b47db1e25869096191424bc`.  
Production source branch: `main`.

Accepted PR #164 head passed **26/26 workflows** with zero failures. The first main push passed **25/26**; `Release RC Truth CI` correctly failed closed against the older boundary. The merge differs from the tested head only by the exact already-accepted PR #163 operational merge-guard files recorded in `release/current-rc.json`.

## Current product delta

- Public booking request now shows the exact owner-approved server-confirmed Russian message: `Заявка отправлена. Номер заявки <id>. Менеджер свяжется с вами для согласования условий и предоплаты.`
- The Public flow still states that a request is not yet a confirmed reservation.
- Marketing remains part of final Admin/Core and includes consent/attribution and automation contracts.
- Agent CRM/reporting and Reception agent filtering are active.
- Dated maintenance/manual room holds are part of Reception operations.
- Extra-bed restrictions are enforced in Resort Core for the three owner-approved denied room categories.
- Returning guests with a prior completed stay receive the automatic 10% accommodation discount; alternative discounts remain auditable.
- Booking schedule drag/drop remains preview + explicit confirmation before commit.
- Existing security, Kitchen/Dining, Guest OS, realtime, backup/restore and release hardening remain active.

## Property/database authority

Canonical property truth remains **84 rooms / 12 categories / 48 rates**. Frozen database boundary remains **24 committed migrations / 93 critical domain constraints**.

External staging/production uses `npx prisma migrate deploy`, never `prisma db push` as release evidence.

## Full Test evidence

Railway `Three Crowns Full Test` has successful application services and PostgreSQL. Verified operational evidence includes external HTTPS/WSS smoke, scheduled browser acceptance, explicit application restart policy and a read-only 50-VU load baseline of **32,229 HTTP requests with 0% failures**. This remains Full Test evidence, not real hotel production cutover evidence.

## Product authority boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation/payment authority.
- AI/n8n do not confirm payment or guarantee reservations.
- Kitchen/Dining totals do not automatically create Hotel Payments.
- Room QR/PIN is not a physical lock credential.
- Real MKassa/TTHotel/TTLock remain provider/hardware gated.
- NFC acquiring/wallet remains deferred outside active V1.
- Google Drive/Sheets are control/archive/mirror surfaces, not transaction truth.

## External production remains fail-closed

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until real target-host, platform branch protection/permissions, rollback, final production HTTPS/WSS, device/provider, fresh backup/restore/off-site, immutable deployment linkage, DNS rollback and explicit owner GO evidence exists.

Historical release files remain reference evidence only and do not override the current machine manifest and canonical state documents.
