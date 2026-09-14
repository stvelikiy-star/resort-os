FROM node:22-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates \
    && python3 -m venv /opt/venv \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt ./requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY packages/database/package.json packages/database/package-lock.json ./packages/database/
RUN cd packages/database && npm ci --no-audit --no-fund

COPY packages/database ./packages/database
COPY services/api ./services/api
COPY scripts ./scripts
COPY data-intake ./data-intake
COPY deploy/prepare_railway_fulltest.py ./deploy/prepare_railway_fulltest.py

RUN /opt/venv/bin/python - <<'PY'
from pathlib import Path
p = Path('/app/services/api/app/stays.py')
s = p.read_text()
if 'import os\n' not in s:
    s = s.replace('import hashlib\n', 'import hashlib\nimport os\n', 1)
s = s.replace('pin = f"{secrets.randbelow(1_000_000):06d}"', 'pin = os.environ.get("TEST_GUEST_FIXED_PIN") or f"{secrets.randbelow(1_000_000):06d}"', 1)
p.write_text(s)
PY

# The full-test Railway image composes the MKassa adapter without changing the
# stable source composition order used by the rest of the monorepo.
RUN /opt/venv/bin/python - <<'PY'
from pathlib import Path
p = Path('/app/services/api/app/app_entry.py')
s = p.read_text()
import_line = 'from .mkassa_payment_bridge import router as mkassa_payment_bridge_router\n'
if import_line not in s:
    anchor = 'from .marketing_automation import router as marketing_automation_router\n'
    s = s.replace(anchor, anchor + import_line, 1)
include_line = 'app.include_router(mkassa_payment_bridge_router)\n'
if include_line not in s:
    anchor = 'app.include_router(service_point_payments_integration_router)\n'
    s = s.replace(anchor, anchor + include_line, 1)
p.write_text(s)
PY

EXPOSE 8000

CMD ["sh","-lc","cd /app/packages/database && npx prisma migrate deploy && cd /app && /opt/venv/bin/python scripts/seed_from_intake.py && /opt/venv/bin/python deploy/prepare_railway_fulltest.py && /opt/venv/bin/python scripts/bootstrap_owner.py && APP_ENV=staging /opt/venv/bin/python scripts/bootstrap_staging_staff.py && STAFF_USERNAME=\"$KITCHEN_USERNAME\" STAFF_PASSWORD=\"$KITCHEN_PASSWORD\" STAFF_DISPLAY_NAME='Test Kitchen' STAFF_ROLE=DINING_STAFF /opt/venv/bin/python scripts/upsert_staff_user.py && STAFF_USERNAME=\"$WAITER_USERNAME\" STAFF_PASSWORD=\"$WAITER_PASSWORD\" STAFF_DISPLAY_NAME='Test Waiter' STAFF_ROLE=DINING_STAFF /opt/venv/bin/python scripts/upsert_staff_user.py && exec /opt/venv/bin/python -m uvicorn app.app_entry:app --app-dir services/api --host 0.0.0.0 --port 8000 --proxy-headers"]
