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

EXPOSE 8000

CMD ["sh","-lc","cd /app/packages/database && npx prisma migrate deploy && cd /app && python scripts/seed_from_intake.py && python scripts/bootstrap_owner.py && APP_ENV=staging python scripts/bootstrap_staging_staff.py && exec python -m uvicorn app.app_entry:app --app-dir services/api --host 0.0.0.0 --port 8000 --proxy-headers"]
