FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts ./scripts
COPY data-intake ./data-intake
CMD ["sh","-lc","python scripts/seed_from_intake.py && python scripts/bootstrap_owner.py && python scripts/bootstrap_staging_staff.py && echo BOOTSTRAP_OK && sleep infinity"]
