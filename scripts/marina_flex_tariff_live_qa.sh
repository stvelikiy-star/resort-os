#!/usr/bin/env bash
set -euo pipefail
test "$GITHUB_ACTIONS" = true
umask 077
qa_dir=$(mktemp -d)
qa_pg="flex-tariff-qa-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"
cleanup() {
  for pid in $(jobs -p); do kill "$pid" 2>/dev/null || true; done
  docker rm -f "$qa_pg" >/dev/null 2>&1 || true
  rm -rf "$qa_dir"
}
trap cleanup EXIT
echo "Connected FLEX QA checkout $(git rev-parse HEAD)"
export PGHOST=127.0.0.1 PGPORT=5457 PGUSER=flex_ci PGDATABASE=flex_qa
export PGPASSWORD=$(openssl rand -hex 24)
docker run -d --name "$qa_pg" -p 127.0.0.1:5457:5432 -e POSTGRES_DB=flex_qa \
  -e POSTGRES_USER=flex_ci -e POSTGRES_PASSWORD="$PGPASSWORD" postgres:16 >/dev/null
for n in {1..60}; do pg_isready -q && break; sleep 1; done
db() { psql -X -q -v ON_ERROR_STOP=1 "$@"; }

# One private CA for the three runner-local TLS endpoints.
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=FLEX-Disposable-QA-CA \
  -keyout "$qa_dir/ca.key" -out "$qa_dir/ca.crt" 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj /CN=127.0.0.1 \
  -keyout "$qa_dir/server.key" -out "$qa_dir/server.csr" 2>/dev/null
echo 'subjectAltName=IP:127.0.0.1,DNS:localhost' > "$qa_dir/extensions"
openssl x509 -req -in "$qa_dir/server.csr" -CA "$qa_dir/ca.crt" -CAkey "$qa_dir/ca.key" \
  -CAcreateserial -days 1 -extfile "$qa_dir/extensions" -out "$qa_dir/server.crt" 2>/dev/null
for file in server.crt server.key; do docker cp "$qa_dir/$file" "$qa_pg:/tmp/$file"; done
docker exec "$qa_pg" sh -c 'chown postgres:postgres /tmp/server.key /tmp/server.crt && chmod 600 /tmp/server.key'
db -c "ALTER SYSTEM SET ssl_cert_file='/tmp/server.crt'" -c "ALTER SYSTEM SET ssl_key_file='/tmp/server.key'" \
   -c "ALTER SYSTEM SET ssl=on" -c "SELECT pg_reload_conf()"
export PGSSLROOTCERT="$qa_dir/ca.crt" PGSSLMODE=verify-full NODE_EXTRA_CA_CERTS="$qa_dir/ca.crt"
for n in {1..15}; do db -c 'SELECT 1' >/dev/null 2>&1 && break; sleep 1; done
for file in docs/flex/sql/00*.sql; do
  case "$file" in */0009_*) continue;; esac
  db -f "$file" >/dev/null
done
db -f scripts/marina_flex_rls_isolation_contract.sql >/dev/null
auth_password=$(openssl rand -hex 24)
api_password=$(openssl rand -hex 24)
db -v auth_password="$auth_password" -v api_password="$api_password" <<'SQL'
INSERT INTO flex_skus(sku,title,capability_key,product_status,is_core)
VALUES ('TARIFF_E2E','QA add-on','qa.tariff.live','AVAILABLE',false);
INSERT INTO flex_price_versions(sku,version,monthly_price,currency,valid_from)
VALUES ('TARIFF_E2E',1,4000,'KGS',now()-interval '1 day');
ALTER SCHEMA public RENAME TO flex_private;
REVOKE ALL ON SCHEMA flex_private FROM PUBLIC;
CREATE ROLE flex_auth_runtime LOGIN NOINHERIT PASSWORD :'auth_password';
CREATE ROLE flex_qa_read_runtime LOGIN NOINHERIT PASSWORD :'api_password';
CREATE SCHEMA flex_auth AUTHORIZATION flex_ci;
GRANT USAGE ON SCHEMA flex_auth TO flex_auth_runtime;
ALTER ROLE flex_auth_runtime IN DATABASE flex_qa SET search_path=flex_auth;
ALTER ROLE flex_qa_read_runtime IN DATABASE flex_qa SET search_path=flex_private;
GRANT flex_hotel_reader,flex_identity_reader,flex_platform_admin_reader,flex_catalog_draft_writer,
      flex_agent_statement_reader,flex_investor_statement_reader,flex_platform_statement_reader
      TO flex_qa_read_runtime WITH INHERIT FALSE, SET TRUE;
GRANT USAGE ON SCHEMA flex_private TO flex_qa_read_runtime,flex_hotel_reader,flex_identity_reader,
      flex_platform_admin_reader,flex_catalog_draft_writer,flex_agent_statement_reader,
      flex_investor_statement_reader,flex_platform_statement_reader;
SQL

export FLEX_ENVIRONMENT=qa FLEX_AUTH_ENABLED=true FLEX_AUTH_SCHEMA_READY=true FLEX_MFA_BRIDGE_ENABLED=true
export FLEX_ENABLE_QA_CATALOG_DRAFTS=true FLEX_MFA_KEY_ID=ci-local FLEX_API_AUDIENCE=flex-local
export FLEX_PUBLIC_ORIGIN=https://127.0.0.1:3443 BETTER_AUTH_URL=https://127.0.0.1:3443
export FLEX_AUTH_AUDIENCE="$FLEX_API_AUDIENCE" FLEX_AUTH_ISSUER="$FLEX_PUBLIC_ORIGIN" FLEX_API_ORIGIN=https://127.0.0.1:8443
export FLEX_CATALOG_ADMIN_API_ORIGIN="$FLEX_API_ORIGIN"
export FLEX_DATABASE_URL="postgresql://flex_qa_read_runtime:$api_password@127.0.0.1:5457/flex_qa?sslmode=verify-full"
export FLEX_AUTH_DATABASE_URL="postgresql://flex_auth_runtime:$auth_password@127.0.0.1:5457/flex_qa?sslmode=verify-full"
export FLEX_SESSION_KEY=$(openssl rand -base64 32) BETTER_AUTH_SECRET=$(openssl rand -hex 48)
export QA_PASSWORD=$(openssl rand -hex 24) QA_EMAIL=qa-admin@example.test
export QA_TLS_CERT="$qa_dir/server.crt" QA_TLS_KEY="$qa_dir/server.key"
openssl genpkey -algorithm ED25519 -out "$qa_dir/issuer.key"
export FLEX_MFA_PRIVATE_KEY="$(cat "$qa_dir/issuer.key")"
export FLEX_AUTH_PUBLIC_KEYS_JSON="$(openssl pkey -in "$qa_dir/issuer.key" -pubout | jq -Rs '{"ci-local":.}')"

# Create a normal invitation-backed account. Database grants determine its platform role.
(
 cd apps/flex-console
 node --input-type=module <<'JS'
import pg from 'pg';
import {randomBytes, createHash, randomUUID} from 'node:crypto';
import {getMigrations} from 'better-auth/db/migration';
import {hashPassword} from 'better-auth/crypto';
import {createFlexAuthConfig} from './auth/identity-enabled.mjs';
import {redeemFirstInvite} from './auth/first-invite.mjs';
const db = new pg.Pool({options:'-c search_path=flex_auth'});
try {
  const auth=createFlexAuthConfig({database:db,baseURL:process.env.BETTER_AUTH_URL});
  await (await getMigrations(auth.options)).runMigrations();
  await db.query('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA flex_auth TO flex_auth_runtime');
  const token=randomBytes(32).toString('base64url');
  const email=process.env.QA_EMAIL;
  await db.query('INSERT INTO verification(id,identifier,value,"expiresAt","createdAt","updatedAt") VALUES($1,$2,$3,now()+interval \'10 minutes\',now(),now())',
    [randomUUID(),'flex-first:'+createHash('sha256').update(token).digest('hex'),email]);
  if(!await redeemFirstInvite(db,token,process.env.QA_PASSWORD,hashPassword))throw Error('QA invitation failed');
  await db.query("INSERT INTO flex_private.flex_platform_memberships(subject_id,role,active) SELECT id,'SUPER_ADMIN',true FROM flex_auth.\"user\" WHERE email=$1",[email]);
} finally { await db.end(); }
JS
)
# Runtime processes receive only their own DB credential.
(
 unset PGPASSWORD PGUSER QA_PASSWORD FLEX_AUTH_DATABASE_URL FLEX_MFA_PRIVATE_KEY FLEX_SESSION_KEY BETTER_AUTH_SECRET
 exec python -m uvicorn index:app --app-dir apps/flex-api-qa --host 127.0.0.1 --port 8443 \
   --ssl-keyfile "$QA_TLS_KEY" --ssl-certfile "$QA_TLS_CERT"
) >"$qa_dir/api.log" 2>&1 &
(
 cd apps/flex-console
 unset PGPASSWORD PGUSER QA_PASSWORD FLEX_DATABASE_URL
 exec node --input-type=module <<'JS'
import https from 'node:https';
import fs from 'node:fs';
import {handler} from './server.mjs';
https.createServer({key:fs.readFileSync(process.env.QA_TLS_KEY),cert:fs.readFileSync(process.env.QA_TLS_CERT)},handler).listen(3443,'127.0.0.1');
JS
) >"$qa_dir/console.log" 2>&1 &
for endpoint in "$FLEX_API_ORIGIN/health" "$FLEX_PUBLIC_ORIGIN/api/status"; do
  if ! curl --silent --show-error --fail --retry 12 --retry-delay 1 --retry-all-errors \
       --cacert "$PGSSLROOTCERT" "$endpoint"; then tail -40 "$qa_dir/api.log" "$qa_dir/console.log"; exit 1; fi
done
export QA_TLS_PIN="$(openssl x509 -in "$QA_TLS_CERT" -pubkey -noout | openssl pkey -pubin -outform der | openssl dgst -sha256 -binary | openssl base64 -A)"
if ! python scripts/marina_flex_tariff_live_browser.py; then
  grep -E 'GET /v1/|POST /v1/|asyncpg.exceptions|UndefinedTable|PermissionError|InsufficientPrivilege|RuntimeError' "$qa_dir/api.log" | tail -25 || true
  exit 1
fi
