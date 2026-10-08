# MARINA SMART — current candidate state

Date: 2026-10-08

This document describes the MARINA SMART multi-tenant candidate in PR #234. It
does not replace the active production boundary until staging, isolation,
backup/restore, rollback and owner acceptance are complete.

## Candidate identity

- Repository: stvelikiy-star/resort-os
- PR: #234
- Branch: marina-smart/multi-tenant-foundation-20261008
- Candidate commit: 3734e5190808508142252700d253675f13540ab8
- CI: 41/41 SUCCESS
- Candidate manifest: release/marina-smart-current-candidate.json
- Migration candidate: 31 committed migrations

## Architecture decision

MARINA SMART uses a central SaaS runtime and database infrastructure. Every
customer is an isolated Tenant. Every hotel/resort is a Property belonging to a
Tenant. Customer domains are public-site entry points; they are not the
customer database or application server.

The existing roles, navigation and approved compact chessboard remain unchanged.
MARINA SMART is not merged with Three Crowns product data or user-facing
branding.

## Implemented in this candidate

- tenants table and property tenantId;
- deterministic legacy backfill;
- tenant-aware seed/bootstrap;
- trusted database-derived tenant_id and property_id auth context;
- manual read-only staging foundation gate;
- explicit production flag MARINA_TENANT_CONTEXT_ENABLED=false.

## Deliberately not claimed yet

- external Marina staging verification;
- two-tenant cross-tenant login/read/write E2E;
- complete tenant-scoped coverage of every read/write/realtime/background path;
- production backup/restore and rollback on the target;
- production DNS, HTTPS/WSS and device acceptance;
- production cutover authorization.

## Gate order

1. Deploy this candidate to isolated staging.
2. Create two synthetic tenants and two properties.
3. Run the read-only foundation gate.
4. Run browser/API isolation tests for login, reads, writes, roles, Guest OS,
   AI, realtime and background tasks.
5. Run backup/restore and rollback rehearsal.
6. Only then consider enabling tenant context and preparing production.
