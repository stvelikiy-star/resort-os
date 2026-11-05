#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

command -v docker >/dev/null || { echo "ERROR: Docker is not installed"; exit 1; }
docker compose version >/dev/null || { echo "ERROR: Docker Compose plugin is required"; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: Python 3 is needed to generate credentials"; exit 1; }

ENV_FILE=".marina-demo.env"
if [[ ! -f "$ENV_FILE" ]]; then
  python3 - <<'PY'
from pathlib import Path
import secrets
p=Path(".marina-demo.env")
# O_EXCL prevents accidental overwrite and follows the explicit first-run model.
with p.open("x") as f:
    f.write("MARINA_DEMO_DB_PASSWORD="+secrets.token_hex(24)+"\n")
    f.write("MARINA_DEMO_OWNER_USERNAME=demo-owner\n")
    f.write("MARINA_DEMO_OWNER_PASSWORD="+secrets.token_urlsafe(24)+"\n")
p.chmod(0o600)
PY
fi
chmod 600 "$ENV_FILE"
echo "MARINA SMART demo: building isolated services and migrating empty database..."
docker compose --env-file "$ENV_FILE" -f compose.marina-demo.yaml up -d --build --wait
echo
echo "MARINA SMART running:"
echo "  Admin: http://127.0.0.1:13001"
echo "  Web:   http://127.0.0.1:13000"
echo "  Staff: http://127.0.0.1:13002"
echo
echo "  Username: $(sed -n 's/^MARINA_DEMO_OWNER_USERNAME=//p' "$ENV_FILE")"
echo "  Password: $(sed -n 's/^MARINA_DEMO_OWNER_PASSWORD=//p' "$ENV_FILE")"
echo
echo "Synthetic data only. Do not publicly expose these ports."
