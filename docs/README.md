# Three Crowns Resort OS — documentation authority

Status: **CURRENT DOCUMENTATION INDEX**  
Date: **2026-09-02**

This file prevents dated handoff/demo/runbook artifacts from overriding the current release truth.

## Current release authority

Use these sources, in this order, for release and launch decisions:

1. `release/current-rc.json` — machine-readable frozen RC boundary and production-source restrictions.
2. `knowledge/04_CURRENT_STATE.md` — current implemented product/system state.
3. `knowledge/09_LAUNCH_ACCEPTANCE.md` — mandatory external acceptance and cutover sequence.
4. `docs/DEPLOYMENT_RUNBOOK.md` — current controlled deployment/runbook contract.
5. GitHub issue `#39` — live launch board for unresolved release evidence.

If a dated document conflicts with one of the sources above, the current sources above win.

## Current room authority

The production room-register authority is repository-controlled:

- `data-intake/rooms.csv` — canonical 84-room / 12-category physical register;
- `data-intake/room-register-owner-approval.json` — checksum-bound OWNER_APPROVED evidence;
- `data-intake/owner-room-checklist.json` — historical questionnaire/provenance only.

A Google Sheet/old import file must not be used as a second mutable production room authority.

Before external launch, the remaining room task is **target reconciliation** against the canonical register:

`dry-run -> exact diff review -> safe apply -> zero diff`

Do not reopen the room questionnaire merely because a dated handoff/runbook says owner confirmation is incomplete.

## Database release authority

The committed production/staging release ledger contains exactly eight migrations:

1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`
5. `4_guest_engagements`
6. `5_guest_os_core`
7. `6_service_point_qr_operations`
8. `7_kitchen_operations`

External staging and production use:

```bash
npx prisma migrate deploy
```

`prisma db push` is allowed only for explicitly disposable/local test databases when a current test/runbook says so. It is not release evidence and must not replace the eight-migration ledger on an external acceptance target.

## Current product boundaries

- `ReservationRequest != Reservation`.
- OWNER/MANAGER retain reservation/payment authority.
- AI/n8n do not confirm payment, create a guaranteed Reservation, invent a fixed prepayment percentage/payment route, or bypass Core availability/pricing.
- Growth outbound authority is `NONE_AUTOMATIC`.
- Kitchen operational totals do not automatically create Hotel Payment or mutate accommodation total.
- NFC wallet/acquiring is **DEFERRED** and must remain absent from active V1 runtime.
- Google Drive/Sheets are knowledge/control/mirror surfaces, not transaction truth.

## Dated / historical / reference artifacts

The following filenames contain valuable historical evidence or local mechanics but are **not current release authority by themselves**:

- `docs/STAGING_RUNBOOK_2026-08-28.md` — historical/local staging mechanics; its old room-authority statements are superseded by the repository OWNER_APPROVED register and current deployment runbook. External staging must follow the current release contract.
- `docs/DELIVERY_HANDOFF_2026-08-30.md` — historical handoff snapshot (old PR/SHA/workflow counts).
- `docs/RELEASE_CANDIDATE_2026-08-28.md` — historical RC snapshot.
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md` — source-reconciliation provenance; old public-site/payment claims can be stale.

Historical Vercel previews, ZIP/HTML snapshots and stale `main` are also reference/demo only. They cannot override `release/current-rc.json` or current knowledge.

## External launch is still fail-closed

A green repository is not external production evidence. Production cutover remains blocked until the required real evidence exists, including:

- branch protection/required checks;
- safe Drive access governance for launch-control data;
- target room reconciliation;
- actual host/account preflight;
- verified legacy rollback package;
- isolated external HTTPS/WSS staging;
- external public-truth and business acceptance;
- real-device acceptance;
- E2E for providers actually enabled at launch;
- monitoring/alerting/backups/restore evidence;
- fresh pre-cutover backup and exact DNS rollback capture;
- explicit OWNER GO.

Do not infer any of these from CI, a Vercel preview, a dated document, or the existence of a template.
