#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/srv/three-crowns}"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.production}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/compose.production.yaml}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_CLIENT_IMAGE="${POSTGRES_CLIENT_IMAGE:-postgres:16-alpine}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_DIR}/${STAMP}"

read_env_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    return 0
  fi
  awk -v prefix="${key}=" 'index($0,prefix)==1 {print substr($0,length(prefix)+1)}' "${ENV_FILE}" | tail -n 1
}

setting() {
  local key="$1"
  local fallback="${2:-}"
  local current="${!key-}"
  if [[ -n "${current}" ]]; then
    printf '%s' "${current}"
    return
  fi
  current="$(read_env_value "${key}")"
  if [[ -n "${current}" ]]; then
    printf '%s' "${current}"
  else
    printf '%s' "${fallback}"
  fi
}

bool_true() {
  case "${1,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

mkdir -p "${TARGET}"
chmod 700 "${BACKUP_DIR}" "${TARGET}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing production env: ${ENV_FILE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

DB_BACKUP_MODE="$(setting DB_BACKUP_MODE compose)"
case "${DB_BACKUP_MODE}" in
  compose)
    # CI-verified legacy/single-server mode. PostgreSQL remains private to Compose.
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres \
      sh -c 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl -Fc' \
      > "${TARGET}/postgres.dump"
    ;;
  url)
    # Managed PostgreSQL / DBaaS mode. Prefer a pg_dump-safe URL without Prisma's
    # schema= query parameter; sslmode and other managed-DB transport settings stay.
    PG_DUMP_DATABASE_URL="$(setting PG_DUMP_DATABASE_URL)"
    if [[ -z "${PG_DUMP_DATABASE_URL}" ]]; then
      PG_DUMP_DATABASE_URL="$(setting DATABASE_URL)"
    fi
    if [[ -z "${PG_DUMP_DATABASE_URL}" ]]; then
      echo "DB_BACKUP_MODE=url requires PG_DUMP_DATABASE_URL or DATABASE_URL" >&2
      exit 1
    fi
    if [[ "${PG_DUMP_DATABASE_URL}" == *"schema="* ]]; then
      echo "PG_DUMP_DATABASE_URL must not contain Prisma-only schema=; provide a pg_dump-safe URL preserving sslmode" >&2
      exit 1
    fi
    docker run --rm \
      --env "PG_DUMP_DATABASE_URL=${PG_DUMP_DATABASE_URL}" \
      "${POSTGRES_CLIENT_IMAGE}" \
      sh -ec 'exec pg_dump "$PG_DUMP_DATABASE_URL" --no-owner --no-acl -Fc' \
      > "${TARGET}/postgres.dump"
    ;;
  *)
    echo "Unsupported DB_BACKUP_MODE=${DB_BACKUP_MODE}; expected compose or url" >&2
    exit 1
    ;;
esac

if [[ ! -s "${TARGET}/postgres.dump" ]]; then
  echo "PostgreSQL backup is empty" >&2
  exit 1
fi

# Back up operational media without following external symlinks.
if [[ -d "${ROOT_DIR}/data/media" ]]; then
  tar -C "${ROOT_DIR}/data" -czf "${TARGET}/media.tar.gz" media
fi

# n8n persistent state is operational automation state, never hotel booking truth.
if [[ -d "${ROOT_DIR}/data/n8n" ]]; then
  tar -C "${ROOT_DIR}/data" -czf "${TARGET}/n8n.tar.gz" n8n
fi

sha256sum "${TARGET}"/* > "${TARGET}/SHA256SUMS"

# Never copy .env.production into backup archives.
find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf {} +

OFFSITE_REQUIRED="$(setting OFFSITE_BACKUP_REQUIRED false)"
S3_ENDPOINT_URL="$(setting S3_ENDPOINT_URL)"
S3_REGION="$(setting S3_REGION)"
S3_BUCKET="$(setting S3_BACKUP_BUCKET)"
S3_PREFIX="$(setting S3_BACKUP_PREFIX three-crowns)"
S3_ACCESS_KEY_ID="$(setting S3_ACCESS_KEY_ID)"
S3_SECRET_ACCESS_KEY="$(setting S3_SECRET_ACCESS_KEY)"

S3_CONFIGURED=true
for value in "${S3_ENDPOINT_URL}" "${S3_REGION}" "${S3_BUCKET}" "${S3_ACCESS_KEY_ID}" "${S3_SECRET_ACCESS_KEY}"; do
  if [[ -z "${value}" ]]; then
    S3_CONFIGURED=false
  fi
done

if [[ "${S3_CONFIGURED}" != true ]]; then
  if bool_true "${OFFSITE_REQUIRED}"; then
    echo "OFFSITE_BACKUP_REQUIRED=true but S3 backup settings are incomplete" >&2
    exit 1
  fi
  echo "WARN: off-site S3 backup not configured; local backup only"
else
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required for S3 off-site upload" >&2
    exit 1
  fi
  if ! curl --help all 2>/dev/null | grep -q -- '--aws-sigv4'; then
    echo "curl build does not support --aws-sigv4 required for S3 off-site upload" >&2
    exit 1
  fi

  S3_ENDPOINT_URL="${S3_ENDPOINT_URL%/}"
  S3_PREFIX="${S3_PREFIX#/}"
  S3_PREFIX="${S3_PREFIX%/}"
  CURL_CONFIG="$(mktemp)"
  chmod 600 "${CURL_CONFIG}"
  trap 'rm -f "${CURL_CONFIG}"' EXIT
  cat > "${CURL_CONFIG}" <<EOF
silent
show-error
fail
aws-sigv4 = "aws:amz:${S3_REGION}:s3"
user = "${S3_ACCESS_KEY_ID}:${S3_SECRET_ACCESS_KEY}"
EOF

  for file in "${TARGET}"/*; do
    name="$(basename "${file}")"
    object_url="${S3_ENDPOINT_URL}/${S3_BUCKET}/${S3_PREFIX}/${STAMP}/${name}"
    curl --config "${CURL_CONFIG}" --upload-file "${file}" "${object_url}"
    # A signed HEAD proves the object is readable with the configured credentials.
    curl --config "${CURL_CONFIG}" --head "${object_url}" >/dev/null
  done
  rm -f "${CURL_CONFIG}"
  trap - EXIT
  echo "OFFSITE_BACKUP=VERIFIED_UPLOAD"
  echo "OFFSITE_PREFIX=s3://${S3_BUCKET}/${S3_PREFIX}/${STAMP}/"
fi

echo "Backup complete: ${TARGET}"
echo "BACKUP_SHA256_FILE=${TARGET}/SHA256SUMS"
