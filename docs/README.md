# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-18**

Use these sources, in order, for current release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary.
2. `knowledge/04_CURRENT_STATE.md` — factual implemented state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — external acceptance and cutover gates.
4. `docs/DEPLOYMENT_RUNBOOK.md` — controlled deployment procedure.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — migration/constraint ledger.
6. dated release files under `docs/RELEASE_*` — historical evidence only.

If a dated historical document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.62.2**.  
Launch profile: **`FULL_NO_PAYMENTS`**.  
Exact tested PR #176 head: `a3ff4c847c66cd64a7cca92ccec613f23917f62d`.  
Accepted executable head: `a53850983d8fc6e1f1997199049a5b071511ed80`.  
Current governance/main head after controlled refreeze: `b20ea27d9fd7950e0a22f164413156e8b62355ec`.  
Production source branch: `main`.

Evidence:
- PR #176: **29/29 workflows SUCCESS**;
- first main push for accepted executable: **25/26 SUCCESS**, with only `Release RC Truth CI` correctly failing closed against the older boundary;
- PR #177 controlled refreeze: **25/25 PR workflows SUCCESS**;
- post-refreeze main: **24/24 SUCCESS**, including Release RC Truth and Resort OS Release Gate.

The executable product boundary remains `a5385098...`; later governance/docs-only merge commits do not replace it.

## Current product contour

Operational launch surfaces:
- Public Web;
- PMS / Reception;
- CRM / Agents / Marketing;
- Staff / housekeeping / maintenance / voice;
- Guest OS;
- Kitchen / Dining;
- n8n / AI-sales orchestration within authority limits;
- realtime / WebSocket.

Launch-disabled/fail-closed surfaces:
- payment mutation routes;
- bank/provider acquiring;
- Service Point payment QR operations;
- MKassa;
- NFC wallet/acquiring.

Guest OS room QR/PIN remains a non-payment guest-service surface and is not a physical smart-lock credential.

TTLock/TTHotel provider work is deferred and is not an active `FULL_NO_PAYMENTS` launch gate.

## Product authority boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation and factual payment authority.
- AI/n8n do not confirm payment or guarantee reservations.
- Kitchen/Dining totals do not automatically create Hotel Payments.
- Dormant provider/payment source code does not imply launch enablement.
- Google Drive/Sheets are control/archive/mirror surfaces, not transaction truth.

## Property/database authority

Canonical property truth remains **84 rooms / 12 categories / 48 rates**.  
Frozen database boundary remains **24 committed migrations / 93 critical domain constraints**.

External staging/production uses `npx prisma migrate deploy`, never `prisma db push` as release evidence.

## External production remains fail-closed

Production remains **EXTERNAL PRODUCTION CUTOVER STOP** until real target-host access, GitHub branch protection, Drive permission evidence, rollback, final HTTPS/WSS, real-device acceptance, fresh backup/restore/off-site evidence, immutable runtime linkage, authoritative DNS rollback and explicit owner GO all exist.

Historical release files remain reference evidence only and do not override the current machine manifest and canonical state documents.
