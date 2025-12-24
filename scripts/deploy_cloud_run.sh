#!/usr/bin/env bash
set -euo pipefail

# Deploy LiteLLM proxy to Cloud Run.
# Usage:
#   PROJECT_ID=my-proj REGION=us-central1 OPENAI_API_KEY=sk-... PROXY_GATEWAY_TOKEN=... ./scripts/deploy_cloud_run.sh
#
# Optional:
#   PROXY_MASTER_KEY=... MAX_INSTANCES=50 MIN_INSTANCES=1 CONCURRENCY=15 IMAGE=gcr.io/$PROJECT_ID/litellm-proxy

: "${PROJECT_ID:?PROJECT_ID required}"
: "${REGION:?REGION required}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY required}"
: "${PROXY_GATEWAY_TOKEN:?PROXY_GATEWAY_TOKEN required}"

IMAGE="${IMAGE:-gcr.io/$PROJECT_ID/litellm-proxy}"
SERVICE="${SERVICE:-litellm-proxy}"
CONCURRENCY="${CONCURRENCY:-15}"
MIN_INSTANCES="${MIN_INSTANCES:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-50}"
PORT="${PORT:-8080}"

echo "Building image $IMAGE"
gcloud builds submit --tag "$IMAGE" .

echo "Deploying service $SERVICE to region $REGION"
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated=false \
  --concurrency="$CONCURRENCY" \
  --min-instances="$MIN_INSTANCES" \
  --max-instances="$MAX_INSTANCES" \
  --cpu=1 \
  --memory=1Gi \
  --set-env-vars PORT="$PORT" \
  --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY",PROXY_GATEWAY_TOKEN="$PROXY_GATEWAY_TOKEN",PROXY_MASTER_KEY="${PROXY_MASTER_KEY:-}"

echo "Done."


