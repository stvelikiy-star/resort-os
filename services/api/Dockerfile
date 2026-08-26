FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api ./services/api
COPY data-intake ./data-intake
COPY scripts/seed_from_intake.py ./scripts/seed_from_intake.py
COPY scripts/bootstrap_owner.py ./scripts/bootstrap_owner.py

RUN useradd --create-home --uid 10001 resort && chown -R resort:resort /app
USER resort

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.app_entry:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
