#!/usr/bin/env bash
set -eu
exec env -i PATH="$PATH" HOME="$HOME" LANG=C.UTF-8 PROPERTY_CODE=BETA APP_ENV=test MARINA_CUSTOMER_SITE_SAFE_MODE=true DATABASE_URL=postgresql://audit@127.0.0.1:55432/marina_fixture "$PWD/runtime/venv/bin/python" -m uvicorn app.app_entry:app --app-dir new/services/api --host 127.0.0.1 --port 18002 --ssl-keyfile runtime/localhost.key --ssl-certfile runtime/localhost.crt
