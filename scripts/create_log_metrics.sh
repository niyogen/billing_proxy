#!/usr/bin/env bash
set -euo pipefail

# Create log-based metrics for LiteLLM proxy.
# Usage:
#   PROJECT_ID=my-proj ./scripts/create_log_metrics.sh

: "${PROJECT_ID:?PROJECT_ID required}"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "Creating litellm_total_tokens (delta counter)"
gcloud logging metrics create litellm_total_tokens \
  --description="Total tokens per request" \
  --log-filter='jsonPayload.message="litellm_request" AND jsonPayload.total_tokens>=0' \
  --value-extractor='EXTRACT(jsonPayload.total_tokens)' \
  --metric-type=delta \
  --unit="1" || true

echo "Creating litellm_cost_usd (delta counter)"
gcloud logging metrics create litellm_cost_usd \
  --description="Cost USD per request" \
  --log-filter='jsonPayload.message="litellm_request" AND jsonPayload.cost_usd>0' \
  --value-extractor='EXTRACT(jsonPayload.cost_usd)' \
  --metric-type=delta \
  --unit="1" || true

echo "Done."

