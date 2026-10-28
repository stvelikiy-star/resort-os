FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir asyncpg==0.30.0 argon2-cffi==23.1.0
COPY scripts/provision_empty_marina_property.py ./scripts/provision_empty_marina_property.py
RUN useradd --create-home --uid 10001 marina && chown -R marina:marina /app
USER marina
CMD ["python", "scripts/provision_empty_marina_property.py"]
