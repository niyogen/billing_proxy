# Build a LiteLLM proxy image for Cloud Run with Nginx for Documentation
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and docs
COPY proxy/config.yaml /app/config.yaml
COPY callbacks /app/callbacks
COPY nginx.conf /etc/nginx/nginx.conf
COPY docs /app/docs
COPY start.sh /app/start.sh

# Make start script executable
RUN chmod +x /app/start.sh

# Install python dependencies
RUN pip install --no-cache-dir "litellm[proxy]" google-cloud-logging google-cloud-monitoring asyncpg

# Cloud Run sets PORT
ENV PORT=8080
EXPOSE 8080

CMD ["/app/start.sh"]
