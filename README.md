# Resort OS — Three Crowns

Hospitality operating system for «Три Короны», Cholpon-Ata, Issyk-Kul.

## Current engineering state

Implementation has started. Do not confuse source existence with production readiness.

Current first milestone:

`84 real rooms -> seasonal rates -> availability -> reservation request -> paid reservation -> PMS grid`

Canonical implementation truth is maintained in:
`knowledge/04_CURRENT_STATE.md`.

Three Crowns property specification:
`knowledge/06_THREE_CROWNS_MASTER_SPEC.md`.

Evidence reconciliation:
`docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md`.

## Repository layout

- `services/api/` — FastAPI Resort Core.
- `packages/database/prisma/` — canonical PostgreSQL schema owner.
- `packages/database/sql/` — critical PostgreSQL constraints not expressible in Prisma.
- `scripts/` — database bootstrap / evidence-backed seed.
- `data-intake/` — verified/qualified Three Crowns source inputs.
- `recovery-artifacts/` — recovered prototypes/reference only.
- `knowledge/` — canonical product/domain/current-state documents.

## Local Core startup

Requirements:
- Docker;
- Node.js 22+;
- Python 3.12+.

1. Start PostgreSQL:

```bash
docker compose up -d postgres
```

2. Create a local env file:

```bash
cp .env.example .env
set -a && source .env && set +a
```

3. Build the initial PostgreSQL schema with Prisma:

```bash
cd packages/database
npm install
npx prisma validate
npx prisma db push
cd ../..
```

4. Install API dependencies and apply critical DB constraints:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
python scripts/apply_core_constraints.py
```

5. Load the evidence-backed Three Crowns inventory/rates:

```bash
python scripts/seed_from_intake.py
```

The seed stops if the intake no longer reconciles to exactly 84 rooms and 12 room categories.

6. Start Core API:

```bash
python -m uvicorn app.main:app --app-dir services/api --reload --port 8000
```

Useful endpoints:

- `GET /health`
- `GET /api/v1/booking/check-availability`
- `POST /api/v1/booking/requests`
- `GET /api/v1/pms/grid`
- `/docs` — FastAPI OpenAPI UI in development.

## Critical booking rule

An unpaid customer request is **not an active reservation**.

The legacy public-site rule that allowed a preliminary unpaid booking for two days is stale and must not be implemented.

The exact required prepayment amount/provider is still a business decision and is intentionally not hard-coded in Core.

## Site

A V5 public-site visual skeleton exists separately as a recovered/deployed prototype. It is not yet considered the canonical source-backed public application in this repository. The next site step is to connect its booking UI to verified Core availability and reservation-request endpoints rather than preserve its previous demo-only booking behavior.

## Development rule

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`

No production payment activation, DNS cutover, destructive production DB action, or irreversible production change without an explicit owner gate.
