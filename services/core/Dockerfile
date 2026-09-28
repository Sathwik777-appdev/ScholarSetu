# Build from the repository root:  docker build -f services/core/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd --create-home --uid 10001 app

WORKDIR /app
COPY services/core/requirements.txt .
RUN pip install -r requirements.txt

# Bake the multilingual embedding model (ONNX) into the image so the API never downloads at runtime.
ENV EMBEDDING_CACHE_DIR=/opt/models
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/opt/models')" \
    && chmod -R a+rX /opt/models

COPY services/core/ /app/
COPY rules/ /rules/
COPY adapters/ /adapters/
COPY scripts/seed_demo.py /scripts/seed_demo.py

USER app
EXPOSE 8000
# Migrate (unless RUN_MIGRATIONS=false, e.g. on Cloud Run where a job migrates), then serve on $PORT.
# Secrets (JWT_SECRET, signing key, database URL) are provided at runtime, never baked in.
CMD ["sh", "-c", "if [ \"${RUN_MIGRATIONS:-true}\" != false ]; then alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
