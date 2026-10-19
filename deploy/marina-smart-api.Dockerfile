# MARINA SMART dedicated API image. Build context: repository root.
# Never bootstrap hotel data or run production migrations during web startup.
FROM python:3.12-slim

ARG RELEASE_SHA=UNSET
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RELEASE_SHA=${RELEASE_SHA}

WORKDIR /app
COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/api /app/services/api
RUN useradd --create-home --uid 10001 marina && chown -R marina:marina /app
USER marina
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.app_entry:app", "--app-dir", "services/api", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
