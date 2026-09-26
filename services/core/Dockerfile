# Build from the repository root:  docker build -f services/core/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd --create-home --uid 10001 app

WORKDIR /app
COPY services/core/requirements.txt .
RUN pip install -r requirements.txt

COPY services/core/ /app/
COPY rules/ /rules/
COPY adapters/ /adapters/
COPY scripts/seed_demo.py /scripts/seed_demo.py

USER app
EXPOSE 8000
# Migrate, then serve. Secrets (JWT_SECRET, signing key) are provided at runtime, never baked in.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
