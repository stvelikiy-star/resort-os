#!/usr/bin/env bash
# Read-only launch inventory for MARINA SMART. Never runs compose up, migrations or dumps.
set -euo pipefail
printf 'MARINA SMART TARGET READ-ONLY PREFLIGHT\n'
printf 'UTC: '; date -u +%FT%TZ
printf 'Host: '; hostname
printf 'Git HEAD: '; git rev-parse HEAD 2>/dev/null || echo unavailable
printf 'Docker: '; docker --version
printf '\nExisting MARINA containers (no environment or passwords):\n'
docker ps -a --format '{{.Names}} | {{.Image}} | {{.Status}} | {{.Ports}}' | grep -Ei '(^|[^a-z])(marina|hotel01)([^a-z]|$)' || true
printf '\nMARINA volumes (names only):\n'
docker volume ls --format '{{.Name}}' | grep -Ei 'marina|hotel01' || true
printf '\nHost disk free:\n'
df -h .
printf '\nRequired backup/restore and demo isolation checks:\n'
printf '%s\n' '[ ] Identify active production DB and backup destination (do not print secrets)' '[ ] Save consistent production DB+media backup' '[ ] Restore to isolated disposable DB; verify booking/payment/staff counts' '[ ] Rehearse migration zz114 and rollback on isolated restore' '[ ] Verify production and demo compose projects, DB volumes, credentials and domains differ' '[ ] Confirm both deployments run the identical reviewed commit' '[ ] Perform owner/reception/staff/agent/guest acceptance before real traffic'
printf '\nRESULT: INVENTORY ONLY — NOT PRODUCTION AUTHORIZATION\n'
