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
RUN pip install --no-cache-dir -r requirements.txt

COPY packages/database/package.json packages/database/package-lock.json ./packages/database/
RUN cd packages/database && npm ci --no-audit --no-fund

COPY packages/database ./packages/database
COPY services/api ./services/api
COPY scripts ./scripts
COPY data-intake ./data-intake

RUN python - <<'PY'
from pathlib import Path
p = Path('/app/services/api/app/stays.py')
s = p.read_text()
if 'import os\n' not in s:
    s = s.replace('import hashlib\n', 'import hashlib\nimport os\n', 1)
s = s.replace('pin = f"{secrets.randbelow(1_000_000):06d}"', 'pin = os.environ.get("TEST_GUEST_FIXED_PIN") or f"{secrets.randbelow(1_000_000):06d}"', 1)
p.write_text(s)
PY

EXPOSE 8000

CMD ["sh","-lc","cd /app/packages/database && npx prisma migrate deploy && cd /app && python scripts/seed_from_intake.py && python scripts/bootstrap_owner.py && APP_ENV=staging python scripts/bootstrap_staging_staff.py && STAFF_USERNAME=\"$KITCHEN_USERNAME\" STAFF_PASSWORD=\"$KITCHEN_PASSWORD\" STAFF_DISPLAY_NAME='Test Kitchen' STAFF_ROLE=DINING_STAFF python scripts/upsert_staff_user.py && STAFF_USERNAME=\"$WAITER_USERNAME\" STAFF_PASSWORD=\"$WAITER_PASSWORD\" STAFF_DISPLAY_NAME='Test Waiter' STAFF_ROLE=DINING_STAFF python scripts/upsert_staff_user.py && exec python -m uvicorn app.app_entry:app --app-dir services/api --host 0.0.0.0 --port 8000 --proxy-headers"]
