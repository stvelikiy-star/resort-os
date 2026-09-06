# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-06**

This file prevents dated handoff/demo/runbook artifacts from overriding current release truth.

## Current release authority

Use these sources, in this order, for release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary and production-source restrictions.
2. `knowledge/04_CURRENT_STATE.md` — factual current implemented product/system state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — mandatory external acceptance and cutover sequence.
4. `docs/DEPLOYMENT_RUNBOOK.md` — current controlled deployment/runbook contract.
5. `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — current committed migration/constraint release ledger.
6. `docs/RELEASE_0.61.0_2026-09-06.md` — current release acceptance record.
7. GitHub issue `#39` — live launch board for unresolved external evidence.

If a dated document conflicts with a source above, the current sources above win.

## Current release identity

Release: **Resort OS 0.61.0**.
Accepted executable head: `e1ac7003abe7f63bd306778edd50a1c63dab6f17`.
Observed tree-equivalent main merge: `8e43893c5fd6ba7f997ab7126d0d1dc5b80729e9`.
Production source branch: `main`.

`main` is the canonical source branch after the accepted release merge. This source designation does **not** authorize production cutover while external/governance evidence is incomplete.

## Current room authority

The production room-register authority is repository-controlled:

- `data-intake/rooms.csv` — canonical 84-room / 12-category physical register;
- `data-intake/room-register-owner-approval.json` — checksum-bound OWNER_APPROVED evidence;
- `data-intake/owner-room-checklist.json` — historical questionnaire/provenance only.

Rooms 501/502 are owner-approved two-person basement inventory above the laundry; the superseded mansard/single mapping is not authoritative.

A Google Sheet/old import file must not be used as a second mutable production room authority.

Before external launch, the remaining room task is target reconciliation against the canonical register:

`dry-run -> exact diff review -> safe apply -> zero diff`

Do not reopen the room questionnaire merely because a dated handoff/runbook says owner confirmation is incomplete.

## Database release authority

The frozen 0.61.0 production/staging release ledger contains exactly **22 committed migrations** and the shared release contract fingerprints **87 critical domain constraints** through `scripts/release_contract.py`.

The exact ordered ledger is maintained in `scripts/release_contract.py` and documented in `docs/PRODUCTION_DATABASE_MIGRATIONS.md`.

External staging and production use:

```bash
npx prisma migrate deploy
```

`prisma db push` is allowed only for explicitly disposable/local test databases. It is not release evidence and must not replace the committed migration ledger on an external acceptance target.

## Current product boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation/payment authority.
- AI/n8n do not confirm payment, create a guaranteed Reservation, invent a fixed prepayment percentage/payment route, or bypass Core availability/pricing.
- Growth outbound authority is `NONE_AUTOMATIC`.
- Kitchen/Dining operational totals do not automatically create Hotel Payment or mutate accommodation commercial truth.
- Room QR/Guest PIN is a Guest OS access boundary, not a physical lock credential.
- Real bank acquiring and TTLock actuation remain provider/hardware E2E gated.
- NFC wallet/acquiring is **DEFERRED** outside active V1.
- Google Drive/Sheets are knowledge/control/mirror surfaces, not transaction truth.

## Dated / historical / reference artifacts

The following contain useful historical evidence or local mechanics but are **not current release authority by themselves**:

- `docs/STAGING_RUNBOOK_2026-08-28.md` — historical/local staging mechanics;
- `docs/DELIVERY_HANDOFF_2026-08-30.md` — historical handoff snapshot;
- `docs/RELEASE_CANDIDATE_2026-08-28.md` — historical RC snapshot;
- `docs/RELEASE_0.60.0_2026-09-05.md` — previous frozen release record, superseded by 0.61.0 for current release decisions;
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md` — source-reconciliation provenance.

Historical Vercel previews and ZIP/HTML snapshots are review/reference surfaces only. They cannot override `release/current-rc.json` or current knowledge.

## External launch is still fail-closed

A green repository is not external production evidence. Production cutover remains blocked until required real evidence exists, including:

- branch protection/required checks on `main`;
- safe Drive access governance for launch-control data;
- target room reconciliation;
- actual Beget host/account preflight;
- verified legacy rollback package;
- isolated external HTTPS/WSS staging;
- external public-truth/business acceptance;
- real-device acceptance;
- E2E for providers actually enabled at launch;
- monitoring/alerting/backups/restore evidence;
- fresh pre-cutover backup and exact DNS rollback capture;
- explicit OWNER GO.

Do not infer any of these from CI, a Vercel preview, a dated document, or the existence of a template. **EXTERNAL PRODUCTION CUTOVER STOP** remains in force until the launch-evidence gate is verified.
