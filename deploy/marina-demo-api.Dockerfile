FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/api /app/services/api
COPY scripts/bootstrap_marina_test.py scripts/bootstrap_owner.py scripts/marina_demo_seed.py scripts/marina_demo_restart_e2e.py scripts/marina_ordinary_booking_e2e.py /app/scripts/
RUN useradd -m -u 10001 marina && chown -R marina:marina /app
USER marina
EXPOSE 8000
CMD ["python","-m","uvicorn","app.app_entry:app","--app-dir","services/api","--host","0.0.0.0","--port","8000"]
