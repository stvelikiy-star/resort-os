#!/usr/bin/env bash
set -eu
exec env -i PATH="$PATH" HOME="$HOME" LANG=C.UTF-8 PROPERTY_CODE=ALPHA APP_ENV=test DATABASE_URL=postgresql://audit@127.0.0.1:55432/rollback "$PWD/runtime/venv/bin/python" -m uvicorn app.app_entry:app --app-dir old/services/api --host 127.0.0.1 --port 18002
