#!/bin/sh
set -eu
cd "$(dirname "$0")"

echo "======================================================"
echo "MARINA SMART FULL CLIENT ACCEPTANCE"
echo "======================================================"
echo "Этот тест НЕ сбрасывает базу, но создаёт одну тестовую бронь,"
echo "проводит гостя через check-in/check-out и оставляет историю."
echo

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker Desktop не запущен."
  exit 1
fi

curl -fsS http://127.0.0.1:18100/health/ready >/dev/null
curl -fsS http://127.0.0.1:13101/ >/dev/null
curl -fsS http://127.0.0.1:13102/ >/dev/null

echo "Health/Admin/Staff: PASS"

docker compose -f compose.marina-test.yaml exec -T api \
  env CORE_API_URL=http://127.0.0.1:8000 \
      DATABASE_URL='postgresql://marina_test:MarinaLocalDB2026!@postgres:5432/marina_smart_test?schema=public' \
      PROPERTY_CODE=MARINA_TEST \
      EXPECTED_GUEST_BASE_URL=http://127.0.0.1:18100 \
      BOOTSTRAP_OWNER_USERNAME=marina \
      BOOTSTRAP_OWNER_PASSWORD='MarinaDemo2026!' \
      MAID_USERNAME=housemaid \
      MAID_PASSWORD='MarinaDemo2026!' \
      KITCHEN_USERNAME=kitchen \
      KITCHEN_PASSWORD='MarinaDemo2026!' \
  python scripts/verify_marina_client_cycle.py

echo
echo "======================================================"
echo "MARINA SMART FULL CLIENT ACCEPTANCE = PASS"
echo "======================================================"
