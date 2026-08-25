# THREE CROWNS — CORE IMPLEMENTATION EVIDENCE

Date: 2026-08-25
Status: VERIFIED CI BASELINE

## Commit under verification

`1bc6531a55c5522ad65d60e6a5254988ece9a1cb`

## GitHub Actions

Workflow: `Resort Core CI`
Run: `32834872750`
Job: `97761394147`
Conclusion: `success`
Completed: `2026-08-25T10:00:25Z`

## Verified steps

All of the following completed successfully in the same isolated CI run:

1. PostgreSQL 16 service initialization.
2. Repository checkout.
3. Node.js setup.
4. Prisma dependency installation.
5. `prisma validate`.
6. `prisma db push` against a real PostgreSQL database.
7. Python 3.12 setup.
8. FastAPI dependency installation.
9. Python compile check for `services/api/app` and `scripts`.
10. Critical PostgreSQL constraint application.
11. Evidence-backed Three Crowns seed execution.
12. FastAPI runtime start.
13. `GET /health` smoke test.
14. `GET /api/v1/booking/check-availability` smoke test.
15. `GET /api/v1/pms/grid` smoke test.

## What this verifies

VERIFIED:
- Prisma schema is syntactically valid.
- Schema can be created on PostgreSQL 16.
- custom database constraints can be applied.
- current intake can seed to the database without failing the explicit 84-room / 12-room-type reconciliation checks.
- FastAPI source compiles and starts against the seeded database.
- health, availability and PMS grid endpoints return successful HTTP responses in CI.

## What this does NOT yet verify

NOT YET VERIFIED:
- production deployment;
- production database;
- authentication / RBAC;
- payment integration;
- concurrent booking race test under parallel transactions;
- full price-calculation assertions for every category/date boundary;
- reservation conversion after payment;
- cancellation/refund/no-show flows;
- public site integration;
- staff applications;
- production observability/backups.

The CI result is a development verification baseline, not a production-readiness claim.
