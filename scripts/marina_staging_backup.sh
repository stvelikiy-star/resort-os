#!/usr/bin/env bash
set -euo pipefail
# Isolated MARINA PostgreSQL backup; never alters the source database.
CONTAINER="marina-hotel01-postgres-1"
EXPECTED_PROJECT="${MARINA_COMPOSE_PROJECT:-marina-hotel01}"
BACKUP_DIR="${MARINA_BACKUP_DIR:-/home/agent/marina-backups}"
if [[ "$EXPECTED_PROJECT" != "marina-hotel01" ]]; then
  echo "BLOCK: unexpected MARINA compose project" >&2; exit 1
fi
actual_project="$(docker inspect "$CONTAINER" --format '{{index .Config.Labels "com.docker.compose.project"}}')"
if [[ "$actual_project" != "$EXPECTED_PROJECT" ]]; then
  echo "BLOCK: postgres container does not belong to MARINA" >&2; exit 1
fi
if [[ "$(docker inspect "$CONTAINER" --format '{{.State.Running}}')" != true ]]; then
  echo "BLOCK: MARINA PostgreSQL is not running" >&2; exit 1
fi
if [[ ! -d "$BACKUP_DIR" || ! -w "$BACKUP_DIR" ]]; then
  echo "BLOCK: backup directory missing or not writable: $BACKUP_DIR" >&2; exit 1
fi
umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$(mktemp "$BACKUP_DIR/.marina-predeploy-$stamp-XXXXXXXX.dump")"
target="$BACKUP_DIR/marina-predeploy-$stamp.dump"
if [[ -e "$target" ]]; then
  rm -f "$tmp"; echo "BLOCK: backup target exists" >&2; exit 1
fi
cleanup() { [[ -e "$tmp" ]] && rm -f "$tmp"; }
trap cleanup EXIT
docker exec "$CONTAINER" sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl -Fc' > "$tmp"
if [[ ! -s "$tmp" ]]; then
  echo "BLOCK: empty PostgreSQL archive" >&2; exit 1
fi
# Use the same Postgres client on the DB container for catalog validation.
docker exec -i "$CONTAINER" pg_restore --list < "$tmp" >/dev/null
sha256sum "$tmp" > "$tmp.sha256"
mv -n "$tmp" "$target"
mv "$tmp.sha256" "$target.sha256"
trap - EXIT
echo "MARINA_BACKUP_VERIFIED=$target"
echo "MARINA_BACKUP_SHA256=$(sha256sum "$target" | cut -d' ' -f1)"
