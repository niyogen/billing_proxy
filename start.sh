#!/bin/bash

# Start Billing Service on port 4001
echo "Starting Billing Service on port 4001..."
python /app/proxy/billing_service.py &

# Start LiteLLM in the background on port 4000
# We use & to run it in background
echo "Starting LiteLLM on port 4000..."
litellm --config /app/config.yaml --port 4000 --host 0.0.0.0 &

# Start Nginx in foreground
# Substitute $PORT if needed, but we hardcoded 8080 in nginx.conf for Cloud Run
# Cloud Run injects PORT=8080 by default.
echo "Starting Nginx on port 8080..."
sed -i "s/8080/$PORT/g" /etc/nginx/nginx.conf
nginx -g 'daemon off;'
