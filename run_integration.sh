#!/bin/bash
set -e

# Default directory to script location
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/tests/integration"

echo "=== Building and Starting Services ==="
docker-compose build
docker-compose up -d

echo "=== Waiting for DB to be healthy ==="
# Loop check for DB health
for i in {1..30}; do
  if docker-compose ps db | grep -q "(healthy)"; then
    echo "DB is healthy!"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "DB failed to become healthy"
    docker-compose logs db
    docker-compose down
    exit 1
  fi
  sleep 1
done

echo "=== Running Integration Test ==="
# Install deps for test script if needed (assume python3/pip/venv present or use container)
# We'll run the test script from host for simplicity, assuming deps are there
# But wait, user might not have requests/psycopg2 locally or network access to container ports (5432/8080)
# Ports ARE exposed in compose.
# We need to make sure python deps are installed.
# Using 'pip install' might pollute user env. 
# Better to run the test script INSIDE a container or install to venv.
# Let's try running it locally as per user current state (has pip).
# Or create a 'tester' container.

# Let's try attempting to run locally.
echo "Installing python test deps..."
pip install requests psycopg2-binary --quiet

echo "Running test script..."
python test_full_flow.py
TEST_EXIT_CODE=$?

echo "=== Tearing Down ==="
docker-compose down -v

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Integration Tests Passed"
    exit 0
else
    echo "❌ Integration Tests Failed"
    exit 1
fi
