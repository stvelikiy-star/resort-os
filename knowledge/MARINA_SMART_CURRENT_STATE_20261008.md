# MARINA SMART — current candidate state

Date: 2026-10-16

This document describes the MARINA SMART multi-tenant candidate in PR #234. It
does not replace the active production boundary until staging, isolation,
backup/restore, rollback and owner acceptance are complete.

## Candidate identity

- Repository: stvelikiy-star/resort-os
- PR: #234
- Branch: marina-smart/multi-tenant-foundation-20261008
- Last integrated baseline commit: 52ecdd28bc63c2097eb4011ad2c998703021d38a
- CI: 29/29 SUCCESS on tested PR #241 head 116c65a7aaf50352dc5baf58e52983847f055390 (same tree as integrated baseline)
- Candidate manifest: release/marina-smart-current-candidate.json
- Proposed working migration ledger: 32 migrations; zz108 mappings still requires its own CI evidence before merge.
- The commit above identifies the integrated baseline, not a claim that pending changes have passed CI.

## Architecture decision

Tenant/Property is the customer isolation model.

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
- authenticated two-tenant isolation E2E gate;
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

## Verified disposable CI versus customer deployment

PR #240 added manual external bookings; PR #241 added CSV preview and atomic
batch imports. Two property-specific API processes sharing a disposable database
passed isolation and full restore acceptance (62 public tables at that baseline).
This is not a single-API multi-property login test or a customer-server restore.
The `cross_tenant_e2e_verified` and `backup_restore_target_verified` manifest flags
refer to target deployment acceptance and remain false. No automatic provider is
connected. zz108 adds draft category/rate mappings and one configuration table;
provider access, outbound delivery and real-property acceptance remain pending.
