#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/srv/three-crowns}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/compose.production.yaml}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_DIR}/${STAMP}"

mkdir -p "${TARGET}"
chmod 700 "${BACKUP_DIR}" "${TARGET}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing production env: ${ENV_FILE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

# Logical PostgreSQL backup. The database port is never exposed publicly.
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres \
  sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "${TARGET}/postgres.dump"

# Back up public/private operational media without following external symlinks.
if [[ -d "${ROOT_DIR}/data/media" ]]; then
  tar -C "${ROOT_DIR}/data" -czf "${TARGET}/media.tar.gz" media
fi

# n8n persistent state is backed up separately from PostgreSQL hotel truth.
if [[ -d "${ROOT_DIR}/data/n8n" ]]; then
  tar -C "${ROOT_DIR}/data" -czf "${TARGET}/n8n.tar.gz" n8n
fi

sha256sum "${TARGET}"/* > "${TARGET}/SHA256SUMS"

# Never copy .env.production into backup archives.
find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} +

echo "Backup complete: ${TARGET}"
echo "Copy this directory to the configured off-site target (Google Drive/provider snapshot)."
