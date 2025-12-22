# Build a LiteLLM proxy image for Cloud Run
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY proxy/config.yaml /app/config.yaml
COPY callbacks /app/callbacks

RUN pip install --no-cache-dir "litellm[proxy]" google-cloud-logging google-cloud-monitoring asyncpg

# Cloud Run sets PORT; default to 8080 for local use.
ENV PORT=8080

EXPOSE 8080

CMD ["sh", "-c", "litellm --config /app/config.yaml --port ${PORT:-8080} --host 0.0.0.0"]

