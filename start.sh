#!/bin/bash

# Start Billing Service on port 4001 (REMOVED)
# python /app/proxy/billing_service.py &

# Start LiteLLM in the background on port 4000
# We use & to run it in background
echo "Starting LiteLLM on port 4000..."
litellm --config /app/config.yaml --port 4000 --host 0.0.0.0 --debug &
LITELLM_PID=$!

# Wait for LiteLLM to start (5 seconds)
sleep 5
if ! kill -0 $LITELLM_PID; then
    echo "ERROR: LiteLLM failed to start!"
    exit 1
fi

# Check if port 4000 is listening
echo "Checking LiteLLM health..."
curl -v http://127.0.0.1:4000/health || echo "WARNING: Health check failed"

# Start Nginx in foreground
# Substitute $PORT if needed, but we hardcoded 8080 in nginx.conf for Cloud Run
# Cloud Run injects PORT=8080 by default.
echo "Starting Nginx on port 8080..."
sed -i "s/8080/$PORT/g" /etc/nginx/nginx.conf
nginx -g 'daemon off;' &
NGINX_PID=$!

# Monitor both processes
while kill -0 $LITELLM_PID && kill -0 $NGINX_PID; do
    sleep 1
done

echo "One of the processes exited."
exit 1
