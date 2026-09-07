#!/usr/bin/env bash
set -Eeuo pipefail

cat >&2 <<'MSG'
ERROR: scripts/release_candidate_check.sh is retired.

This legacy helper used `prisma db push`, seeded inventory/staff, and created
synthetic reservation/payment/housekeeping records. It is intentionally no
longer an executable release-evidence path because an unset or mis-scoped
environment could target the wrong database.

Use the canonical guarded paths instead:
  - repository acceptance: GitHub Actions `Resort OS Release Gate`
  - isolated synthetic staging: `Three Crowns Full Staging Gate`
  - production/staging database changes: `npx prisma migrate deploy`
  - production readiness: `python scripts/production_preflight.py`
  - external staging mutations: `python scripts/staging_acceptance.py`

Never use `prisma db push` as release, staging, or production evidence.
MSG

exit 2
