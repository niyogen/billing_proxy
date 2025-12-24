#!/usr/bin/env bash
set -euo pipefail

# Enhanced deployment script for LiteLLM proxy to Cloud Run
# Uses Secret Manager for secure credential management

PROJECT_ID="${PROJECT_ID:-mcpstore-474903}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-litellm-proxy}"
IMAGE="${IMAGE:-gcr.io/$PROJECT_ID/litellm-proxy}"
CONCURRENCY="${CONCURRENCY:-15}"
MIN_INSTANCES="${MIN_INSTANCES:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-50}"
PORT="${PORT:-8080}"

# Database details (Cloud SQL optional; leave SQL_INSTANCE empty for external DB)
SQL_INSTANCE="${SQL_INSTANCE:-}"
SQL_REGION="${SQL_REGION:-us-central1}"
DATABASE_URL="${DATABASE_URL:-}"
PGHOST="${PGHOST:-}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-litellm}"
PGUSER="${PGUSER:-litellm_user}"

echo "==> Building and deploying LiteLLM Proxy to Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE"

# Step 1: Build and push Docker image
echo ""
echo "==> Building Docker image: $IMAGE"
gcloud builds submit --tag "$IMAGE" --project="$PROJECT_ID" .

# Step 2: Determine database connection (Cloud SQL vs external)
echo ""
if [[ -n "$SQL_INSTANCE" ]]; then
  echo "==> Getting Cloud SQL connection details"
  SQL_CONNECTION=$(gcloud sql instances describe "$SQL_INSTANCE" \
    --project="$PROJECT_ID" \
    --format='value(connectionName)')
  SQL_IP=$(gcloud sql instances describe "$SQL_INSTANCE" \
    --project="$PROJECT_ID" \
    --format='value(ipAddresses[0].ipAddress)')
  PGHOST="$SQL_IP"
  USE_CLOUD_SQL=1
  USE_DB_URL=0
  echo "SQL Connection: $SQL_CONNECTION"
  echo "SQL IP: $SQL_IP"
elif [[ -n "$DATABASE_URL" ]]; then
  echo "==> Using external Postgres via DATABASE_URL"
  USE_CLOUD_SQL=0
  USE_DB_URL=1
  echo "DATABASE_URL provided (value hidden)"
else
  echo "==> Using external Postgres host"
  PGHOST="${PGHOST:?PGHOST must be set for external Postgres}"
  PGPORT="${PGPORT:-5432}"
  USE_CLOUD_SQL=0
  USE_DB_URL=0
  echo "PGHOST: $PGHOST"
  echo "PGPORT: $PGPORT"
fi

# Step 3: Deploy to Cloud Run with Secret Manager integration
echo ""
echo "==> Deploying service $SERVICE"
ENV_ARGS=(
  --set-env-vars PORT="$PORT"
  --set-env-vars PGUSER="$PGUSER"
  --set-env-vars PGDATABASE="$PGDATABASE"
  --set-env-vars PGSSL=require
)

if [[ "$USE_DB_URL" -eq 1 ]]; then
  ENV_ARGS+=(--set-env-vars DATABASE_URL="$DATABASE_URL")
else
  ENV_ARGS+=(--set-env-vars PGHOST="$PGHOST" --set-env-vars PGPORT="$PGPORT")
fi

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --concurrency="$CONCURRENCY" \
  --min-instances="$MIN_INSTANCES" \
  --max-instances="$MAX_INSTANCES" \
  --cpu=1 \
  --memory=1Gi \
  --timeout=120 \
  "${ENV_ARGS[@]}" \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-secrets PROXY_GATEWAY_TOKEN=proxy-gateway-token:latest \
  --set-secrets PROXY_MASTER_KEY=proxy-master-key:latest \
  --set-secrets PGPASSWORD=pgpassword:latest \
  --set-secrets STRIPE_API_KEY=stripe-api-key:latest \
  --set-secrets STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest \
  $( [[ "$USE_CLOUD_SQL" -eq 1 ]] && echo "--add-cloudsql-instances=$SQL_CONNECTION" ) \
  --project="$PROJECT_ID"

# Step 4: Get service URL
echo ""
SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --project="$PROJECT_ID" \
  --format='value(status.url)')

echo ""
echo "==> Deployment complete!"
echo "Service URL: $SERVICE_URL"
echo ""
echo "To test with a health check:"
echo "  curl $SERVICE_URL/health"
echo ""
echo "To make an LLM request:"
echo "  PROXY_TOKEN=\$(gcloud secrets versions access latest --secret=proxy-gateway-token)"
echo "  curl -H \"Authorization: Bearer \$PROXY_TOKEN\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}' \\"
echo "    $SERVICE_URL/v1/chat/completions"
echo ""
