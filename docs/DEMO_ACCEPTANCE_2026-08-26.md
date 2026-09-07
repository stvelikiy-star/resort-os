# THREE CROWNS — DEMO / ACCEPTANCE RUNBOOK (HISTORICAL)

Date of original document: 2026-08-26  
Quarantined: 2026-09-07  
Status: **HISTORICAL / DO NOT USE FOR RELEASE, STAGING OR PRODUCTION OPERATIONS**

This file is retained only as historical project context. It is **not** a current execution runbook and must not be used as release evidence.

## Why this document was quarantined

The original 2026-08-26 text contained procedures that are obsolete under Resort OS `0.62.2`, including:

- calling the retired `scripts/release_candidate_check.sh` helper;
- using `prisma db push` in a release/demo procedure;
- referring to old CI infrastructure failures that are no longer current;
- using pre-0.62.x readiness wording and acceptance boundaries.

The retired release-candidate helper now fails closed intentionally. Mutating CI/demo utilities are not deployment tools.

## Current canonical sources

For current release truth use only:

- `release/current-rc.json` — machine-authoritative frozen release boundary;
- `knowledge/04_CURRENT_STATE.md` — current factual product/repository state;
- `knowledge/09_LAUNCH_ACCEPTANCE.md` — launch acceptance boundary;
- `docs/DEPLOYMENT_RUNBOOK.md` — controlled external deployment sequence;
- `docs/SINGLE_SERVER_PRODUCTION_RUNBOOK.md` — approved single-server topology and operations;
- `docs/PRODUCTION_DATABASE_MIGRATIONS.md` — database release rules;
- `docs/RELEASE_0.62.2_2026-09-07.md` — current release record.

## Current release boundary

Resort OS release: `0.62.2`.

Accepted hardened executable head:
`ccf9a7bdca0187ecb712e35d8d0e53bd3d9051cd`

Observed tree-equivalent hardened main merge:
`7cf4b5a3c4164f7224a2fd70807cecf40cfb42bc`

Current release-control main after PR #133:
`dc289a59012207924edf7e75f5d0f50113427c8d`

Frozen database/property contract:
- 22 committed migrations;
- 87 critical domain constraints;
- 84 rooms;
- 12 room categories;
- 48 rate rows.

Public website source remains frozen by owner instruction.

## Safe local/demo rule

Synthetic/demo scripts may run only when their own current fail-closed guards permit the explicitly declared non-production environment. Do not bypass those guards and do not aim them at production services or production PostgreSQL.

Do not use the retired release candidate helper.

For database release/staging evidence use committed migrations:

```bash
cd packages/database
npm ci
npx prisma validate
npx prisma migrate deploy
npx prisma migrate status
cd ../..
```

`prisma db push` is **not** accepted as external staging or production release evidence.

## External launch boundary

Repository CI is not proof of external deployment.

External Beget/VPS work remains pending for:
- real legacy rollback evidence;
- isolated HTTPS/WSS staging;
- exact 22-migration application;
- 84-room reconciliation to zero diff;
- real device/provider acceptance where enabled;
- monitoring and restart/self-healing verification;
- fresh backup -> clean restore -> off-site evidence;
- exact release/image/runtime linkage;
- DNS rollback preparation;
- explicit owner GO.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active.

If any older conversation, note or document points back to the original procedures in this file, treat this quarantine notice and the canonical 0.62.2 sources above as authoritative.