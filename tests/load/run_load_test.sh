#!/bin/bash
set -e

# Default directory to script location
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=== Running Locust Load Test ==="
# -f locustfile.py: file to use
# --headless: no UI
# -u 10: 10 users
# -r 2: 2 users/sec spawn rate
# -t 60s: run for 60 seconds
# --host: target url (localhost:8080)
# --html: report file

locust -f locustfile.py \
       --headless \
       -u 10 -r 2 -t 30s \
       --host http://localhost:8080 \
       --html load_test_report.html

echo "=== Load Test Complete ==="
echo "Check load_test_report.html for details."
