# Deployment & Observability Guide

## Prereqs
- gcloud CLI authenticated to target project.
- Artifact Registry/Container Registry enabled.
- Cloud Run + Cloud Logging/Monitoring enabled.
- Secrets ready: `OPENAI_API_KEY`, `PROXY_GATEWAY_TOKEN`, `PROXY_MASTER_KEY` (optional).

## Build and push
```bash
PROJECT_ID=$(gcloud config get-value project)
REGION=us-central1
IMAGE=gcr.io/$PROJECT_ID/litellm-proxy

gcloud builds submit --tag $IMAGE .
```

## Deploy to Cloud Run
```bash
gcloud run deploy litellm-proxy \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated=false \
  --concurrency=15 \
  --min-instances=1 \
  --max-instances=50 \
  --set-env-vars PORT=8080 \
  --set-env-vars OPENAI_API_KEY=YOUR_KEY,PROXY_GATEWAY_TOKEN=YOUR_GATEWAY_TOKEN,PROXY_MASTER_KEY=OPTIONAL_MASTER \
  --set-env-vars PGHOST=...,PGPORT=5432,PGUSER=...,PGPASSWORD=...,PGDATABASE=...,PGSSL=require \
  --cpu=1 \
  --memory=1Gi
```
- For production, prefer Secret Manager: replace `--set-env-vars` with `--set-secrets OPENAI_API_KEY=projects/$PROJECT_ID/secrets/openai_key:latest` etc.
- Lower `concurrency` for stricter latency; increase for cost efficiency.
- Set `--min-instances` to 0 for scale-to-zero dev environments.

## Health checks
- LiteLLM proxy exposes `/health`. Cloud Run uses its own health check; set a `--timeout` value high enough for large completions.

## Observability (Cloud Logging/Monitoring)
1) **Logs**: Structured JSON emitted by `callbacks/logging.py` flows into Cloud Logging automatically.
2) **Log-based metrics** (examples):
```bash
gcloud logging metrics create litellm_total_tokens \
  --description="Total tokens per request" \
  --log-filter='jsonPayload.message="litellm_request"' \
  --value-extractor='EXTRACT(jsonPayload.total_tokens)' \
  --metric-type=delta \
  --unit="1"

gcloud logging metrics create litellm_cost_usd \
  --description="Cost USD per request" \
  --log-filter='jsonPayload.message="litellm_request" AND jsonPayload.cost_usd>0' \
  --value-extractor='EXTRACT(jsonPayload.cost_usd)' \
  --metric-type=delta \
  --unit="1"
```
3) **Dashboards** (Cloud Monitoring):
   - Charts: tokens/min (group by `labels.tenant_id`), cost/min, P95 latency, 5xx rate, instance count.
   - Use filters on `resource.label.service_name="litellm-proxy"` and labels `tenant_id`, `model`.
4) **Alerts**:
   - Token surge: litellm_total_tokens rate > threshold over 5m.
   - Cost surge: litellm_cost_usd rate > threshold over 5m.
   - Error rate: 5xx ratio > X% over 5m.
   - Latency: P95 > SLO over 5m.

## Networking / Security
- Keep service private if possible; front with HTTPS LB + Cloud Armor if exposing publicly.
- Use bearer token auth (as configured) or IAM with an authenticated Cloud Run ingress.
- Consider VPC connector only if egress controls are required; not needed for public LLM APIs.

## BigQuery export (optional)
- Enable Cloud Logging sink to BigQuery for long-term analytics:
```bash
gcloud logging sinks create litellm-bq-sink bigquery.googleapis.com/projects/$PROJECT_ID/datasets/litellm_logs \
  --log-filter='jsonPayload.message="litellm_request"'
```
- Query tokens/cost per tenant and blend with Cloud Billing export and Stripe data.

## Postgres storage
- Create the table:
```bash
psql "postgres://USER:PASSWORD@HOST:PORT/DB" -f db/schema.sql
```
- Environment variables for the proxy:
  - `PGHOST`, `PGPORT` (default 5432), `PGUSER`, `PGPASSWORD`, `PGDATABASE`
  - `PGSSL=require` (default) or `PGSSL=disable` for local/dev without TLS
- The callback `callbacks.db.log_event` will insert one row per request into `litellm_usage`.

