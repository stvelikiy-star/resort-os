#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/root/data/media/public" "$TMP/root/data/n8n" "$TMP/backups"
printf 'media\n' > "$TMP/root/data/media/public/test.txt"
printf 'n8n\n' > "$TMP/root/data/n8n/state.txt"

cat > "$TMP/root/.env.production" <<'EOF'
DB_BACKUP_MODE=url
PG_DUMP_DATABASE_URL=postgresql://resort:secret@db.example.invalid:5432/resort_os?sslmode=require
OFFSITE_BACKUP_REQUIRED=true
S3_ENDPOINT_URL=https://s3.example.invalid
S3_REGION=test-region-1
S3_BACKUP_BUCKET=three-crowns-backups
S3_BACKUP_PREFIX=production
S3_ACCESS_KEY_ID=TESTACCESSKEY
S3_SECRET_ACCESS_KEY=TESTSECRETKEY
EOF

cat > "$TMP/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# The backup script redirects this stdout to postgres.dump in both compose and
# external-URL modes.
printf 'FAKE-POSTGRES-CUSTOM-DUMP\n'
EOF
chmod +x "$TMP/bin/docker"

cat > "$TMP/bin/curl" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [[ "\${1:-}" == "--help" ]]; then
  printf '%s\n' '     --aws-sigv4 <provider1[:prvdr2[:reg[:srv]]]>'
  exit 0
fi
printf '%s\n' "\$*" >> "$TMP/curl.log"
exit 0
EOF
chmod +x "$TMP/bin/curl"

OUTPUT="$TMP/output.txt"
PATH="$TMP/bin:$PATH" \
ROOT_DIR="$TMP/root" \
ENV_FILE="$TMP/root/.env.production" \
BACKUP_DIR="$TMP/backups" \
RETENTION_DAYS=14 \
bash "$ROOT/scripts/production_backup.sh" | tee "$OUTPUT"

TARGET="$(find "$TMP/backups" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -n "$TARGET"
test -s "$TARGET/postgres.dump"
test -s "$TARGET/media.tar.gz"
test -s "$TARGET/n8n.tar.gz"
test -s "$TARGET/SHA256SUMS"
(
  cd "$TARGET"
  sha256sum -c SHA256SUMS
)

grep -q '^OFFSITE_BACKUP=VERIFIED_UPLOAD$' "$OUTPUT"
grep -q 'three-crowns-backups/production/' "$TMP/curl.log"
grep -q -- '--upload-file' "$TMP/curl.log"
grep -q -- '--head' "$TMP/curl.log"
if grep -q 'TESTSECRETKEY' "$OUTPUT"; then
  echo 'Secret leaked to backup stdout' >&2
  exit 1
fi
if find "$TMP/backups" -type f -name '*env*' | grep -q .; then
  echo 'Environment file leaked into backup directory' >&2
  exit 1
fi

# The pre-existing single-server Compose mode must remain functional.
cat > "$TMP/root/.env.production.compose" <<'EOF'
DB_BACKUP_MODE=compose
POSTGRES_DB=resort_os
POSTGRES_USER=resort
POSTGRES_PASSWORD=secret
OFFSITE_BACKUP_REQUIRED=false
EOF
PATH="$TMP/bin:$PATH" \
ROOT_DIR="$TMP/root" \
ENV_FILE="$TMP/root/.env.production.compose" \
BACKUP_DIR="$TMP/backups-compose" \
COMPOSE_FILE="$TMP/root/compose.production.yaml" \
bash "$ROOT/scripts/production_backup.sh" > "$TMP/compose-output.txt"
COMPOSE_TARGET="$(find "$TMP/backups-compose" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -s "$COMPOSE_TARGET/postgres.dump"
grep -q 'WARN: off-site S3 backup not configured' "$TMP/compose-output.txt"

# Required off-site mode must fail closed when S3 settings are incomplete.
cat > "$TMP/root/.env.production.missing-s3" <<'EOF'
DB_BACKUP_MODE=url
PG_DUMP_DATABASE_URL=postgresql://resort:secret@db.example.invalid:5432/resort_os?sslmode=require
OFFSITE_BACKUP_REQUIRED=true
EOF
if PATH="$TMP/bin:$PATH" ROOT_DIR="$TMP/root" ENV_FILE="$TMP/root/.env.production.missing-s3" BACKUP_DIR="$TMP/backups-missing" bash "$ROOT/scripts/production_backup.sh" >/tmp/three-crowns-backup-missing.out 2>/tmp/three-crowns-backup-missing.err; then
  echo 'Required off-site backup unexpectedly succeeded without S3 configuration' >&2
  exit 1
fi
grep -q 'OFFSITE_BACKUP_REQUIRED=true' /tmp/three-crowns-backup-missing.err

# pg_dump URL must reject Prisma-only schema= in DBaaS mode instead of silently
# passing an invalid libpq URL to pg_dump.
cat > "$TMP/root/.env.production.bad-url" <<'EOF'
DB_BACKUP_MODE=url
PG_DUMP_DATABASE_URL=postgresql://resort:secret@db.example.invalid:5432/resort_os?schema=public&sslmode=require
OFFSITE_BACKUP_REQUIRED=false
EOF
if PATH="$TMP/bin:$PATH" ROOT_DIR="$TMP/root" ENV_FILE="$TMP/root/.env.production.bad-url" BACKUP_DIR="$TMP/backups-bad-url" bash "$ROOT/scripts/production_backup.sh" >/tmp/three-crowns-backup-bad.out 2>/tmp/three-crowns-backup-bad.err; then
  echo 'schema= pg_dump URL unexpectedly accepted' >&2
  exit 1
fi
grep -q 'must not contain Prisma-only schema=' /tmp/three-crowns-backup-bad.err

echo 'PASS: production backup supports DBaaS + required S3, preserves compose mode and fails closed on unsafe configuration'
