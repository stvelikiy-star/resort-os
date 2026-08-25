# THREE CROWNS — PMS / PUBLIC SITE INTEGRATION EVIDENCE

Date: 2026-08-25
Status: VERIFIED DEVELOPMENT CI BASELINE

## Verified run

Workflow: `Resort Core CI`
Run: `32835695344`
Job: `97763917713`
Commit: `7f86165aaebaf38bcf68af415c0f9a3a8311678a`
Conclusion: `success`

## Verified in one CI run

- PostgreSQL 16 starts successfully.
- Prisma schema validates and creates database objects.
- canonical PMS admin dependencies install.
- canonical PMS admin TypeScript check passes.
- canonical PMS admin production build passes.
- canonical public site dependencies install.
- canonical public site TypeScript check passes.
- canonical public site production build passes.
- critical PostgreSQL constraints apply.
- Three Crowns evidence seed reconciles to 84 rooms / 12 room categories.
- FastAPI Core starts.
- health endpoint succeeds.
- availability endpoint succeeds.
- PMS grid endpoint succeeds.
- POST reservation request succeeds.
- POST assertion confirms `is_reservation == false` and status `NEW` for an unpaid request.
- canonical public site starts in production mode.
- public site homepage responds successfully.
- public site `/core` proxy reaches real Core availability successfully.

## Current truth

The following development path is now verified:

`PUBLIC SITE -> CORE AVAILABILITY -> POSTGRESQL`

and:

`PMS ADMIN SOURCE -> LIVE PMS GRID API -> POSTGRESQL`

An unpaid customer submission is verified as a ReservationRequest, not an active Reservation.

## Not production-ready yet

This evidence does NOT prove:
- authentication/RBAC;
- production deployment;
- production database/backups;
- payment/acquiring integration;
- paid request to guaranteed reservation transaction;
- cancellation/refund/no-show handling;
- housekeeping/maintenance workflows;
- production messaging integrations;
- owned media asset migration.
