#!/usr/bin/env bash
# Conservative first launch on AI PROF KG Ubuntu. Does not install packages, modify n8n, Three Crowns, or Railway.
set -euo pipefail
cd "$(dirname "$0")/.."
SLUG="hotel01"
PORT_BASE="15000"
echo "=== MARINA SMART | Ubuntu isolated pilot ==="

if [[ "$(id -u)" == "0" ]]; then
  echo "ERROR: Run as your normal user, not sudo/root." >&2; exit 1
fi
for tool in python3 docker df awk ss curl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $tool" >&2; exit 1
  fi
done
docker compose version >/dev/null
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker engine unavailable to current user. No change made." >&2; exit 1
fi
free_kib=$(df -Pk . | awk 'NR==2 {print $4}')
if [[ "$free_kib" -lt 12582912 ]]; then
  echo "ERROR: Less than 12 GiB disk available. No images or hotel data created." >&2; exit 1
fi
if [[ -r /proc/meminfo ]]; then
  available_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
  if [[ "$available_kib" -lt 1572864 ]]; then
    echo "ERROR: Less than 1.5 GiB RAM currently available. No changes made." >&2; exit 1
  fi
fi

state=".marina-fleet/$SLUG.env"
if [[ ! -f "$state" ]]; then
  # Avoid collisions with any existing Ubuntu service, regardless of whether it is in Docker.
  for port in 15000 15001 15002; do
    if ss -lnt | awk 'NR>1 {print $4}' | grep -Eq "(^|:)$port$"; then
      echo "ERROR: Local port $port is already in use. No hotel created." >&2; exit 1
    fi
  done
  python3 scripts/marina_fleet.py create "$SLUG" --port-base "$PORT_BASE"
else
  echo "Existing hotel config detected; credentials and data will be preserved."
fi

# Docker Compose builds images sequentially on 7-GiB RAM; never stop unrelated containers.
export COMPOSE_PARALLEL_LIMIT=1
python3 scripts/marina_fleet.py start "$SLUG"
echo
echo "=== PRIVATE LOCAL ENDPOINTS ==="
echo "Admin: http://127.0.0.1:15001"
echo "Website: http://127.0.0.1:15000"
echo "Staff: http://127.0.0.1:15002"
for port in 15000 15001 15002; do
  if ! curl -fsS --max-time 6 "http://127.0.0.1:$port/" -o /dev/null; then
    echo "ERROR: UI did not respond on $port; inspect docker compose logs." >&2; exit 1
  fi
done
if ! curl -fsS --max-time 6 http://127.0.0.1:15001/core/health/ready | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["status"]=="ready" and d["property"]=="MARINA_HOTEL01"'; then
  echo "ERROR: Not ready or wrong synthetic hotel. Do not expose publicly." >&2; exit 1
fi
echo "MARINA_UBUNTU_PILOT_PASS: isolated synthetic hotel with all three UIs and healthy API."
echo "Credentials stored locally with 0600 permissions in $state; never upload them."
echo "n8n/ai-prof-postgres/Three Crowns are not modified."
