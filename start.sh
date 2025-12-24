#!/bin/bash

# Start Billing Service on port 4001 (REMOVED)
# python /app/proxy/billing_service.py &

# Start Nginx IMMEDIATELY to satisfy Cloud Run (Port 8080)
echo "Starting Nginx on port 8080..."
sed -i "s/8080/$PORT/g" /etc/nginx/nginx.conf
nginx -g 'daemon off;' &
NGINX_PID=$!

# Run Diagnostics
echo "Current Directory: $(pwd)"
echo "Python Version: $(python --version)"
echo "Installed Packages:"
pip list | grep prisma || echo "Prisma NOT installed"
python -c "import prisma; print('Prisma import check: SUCCESS')" || echo "Prisma import check: FAILED"

# Generate Prisma Client
echo "Generating Prisma Client..."
SCHEMA_PATH=$(find /usr/local/lib -name schema.prisma | grep "litellm/proxy/schema.prisma" | head -n 1)
if [ -z "$SCHEMA_PATH" ]; then
    echo "ERROR: Could not find schema.prisma"
    # Kill Nginx to fail the container if we can't start
    kill $NGINX_PID
    exit 1
fi
echo "Found schema at: $SCHEMA_PATH"
prisma generate --schema "$SCHEMA_PATH"

# Start LiteLLM in the background on port 4000
echo "Starting LiteLLM on port 4000..."
litellm --config /app/config.yaml --port 4000 --host 0.0.0.0 --debug &
LITELLM_PID=$!

# Wait for LiteLLM to start (5 seconds initial check)
sleep 5
if ! kill -0 $LITELLM_PID; then
    echo "ERROR: LiteLLM failed to start immediately!"
    kill $NGINX_PID
    exit 1
fi

# Deep Health Check (Wait up to 120s for migrations/startup)
echo "Checking LiteLLM health via Python (Timeout 120s)..."
if ! python /app/check_port.py; then
    echo "ERROR: LiteLLM failed to bind port 4000 within timeout!"
    kill $LITELLM_PID
    kill $NGINX_PID
    exit 1
fi

# Monitor both processes
echo "All services started. Monitoring..."
while kill -0 $LITELLM_PID && kill -0 $NGINX_PID; do
    sleep 5
done

echo "One of the processes exited."
exit 1
