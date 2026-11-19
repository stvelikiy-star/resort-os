#!/usr/bin/env bash
set -euo pipefail
export PATH="$PWD/runtime/pg16/bin:$PATH"
A=postgresql://audit@127.0.0.1:55431/marina_fixture
B=postgresql://audit@127.0.0.1:55432/marina_fixture
py=runtime/venv/bin/python
umask 077
curl --noproxy '*' -fsS -c runtime/owner.jar -H 'Content-Type: application/json' -d '{"username":"owner","password":"Synthetic-audit-only-2026!"}' http://127.0.0.1:18001/api/v1/auth/login > evidence/pre-login.json
$py scripts/snapshot.py before 55431 marina_fixture
pg_dump -Fc -Z0 "$A" -f runtime/before.dump
sha256sum runtime/before.dump > evidence/dump.sha256
pg_restore --exit-on-error -d "$B" runtime/before.dump
$py scripts/snapshot.py clone 55432 marina_fixture
DATABASE_URL=$B runtime/prisma/node_modules/.bin/prisma migrate deploy --schema new/packages/database/prisma/schema.prisma >evidence/upgrade.log
$py scripts/snapshot.py after 55432 marina_fixture
createdb -h 127.0.0.1 -p 55432 -U audit rollback
pg_restore --exit-on-error -d postgresql://audit@127.0.0.1:55432/rollback runtime/before.dump
$py scripts/snapshot.py rollback 55432 rollback
createdb -h 127.0.0.1 -p 55432 -U audit clean_new
DATABASE_URL=postgresql://audit@127.0.0.1:55432/clean_new runtime/prisma/node_modules/.bin/prisma migrate deploy --schema new/packages/database/prisma/schema.prisma >evidence/new-clean.log
$py scripts/snapshot.py clean 55432 clean_new
