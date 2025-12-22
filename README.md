# LiteLLM Proxy on Google Cloud

Managed, autoscaling LiteLLM proxy on Cloud Run with Cloud Logging/Monitoring and Stripe-ready usage hooks.

## What’s included
- `Dockerfile`: builds a LiteLLM proxy container.
- `proxy/config.yaml`: proxy configuration (models, auth, callbacks).
- `callbacks/logging.py`: structured log callback for tokens, cost, latency.
- `docs/architecture.md`: high-level system design.
- `docs/deployment.md`: deploy + observability steps.
- `docs/stripe-billing.md`: how to integrate Stripe Billing usage.
- `scripts/deploy_cloud_run.sh`: build+deploy helper.
- `scripts/create_log_metrics.sh`: create log-based metrics in Cloud Monitoring.
- `scripts/stripe_usage_reporter.py`: stub for posting batched usage to Stripe.
- `db/schema.sql`: Postgres table for durable usage logs.

## Quick start (local)
```bash
export OPENAI_API_KEY=sk-...
export PROXY_GATEWAY_TOKEN=dev-token
export PROXY_MASTER_KEY=dev-master
pip install "litellm[proxy]" google-cloud-logging google-cloud-monitoring
litellm --config proxy/config.yaml --port 8080 --host 0.0.0.0
# test
curl -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}' \
  http://localhost:8080/v1/chat/completions
```

## Deploy to Cloud Run (summary)
See `docs/deployment.md` for full steps. Outline:
1) Build and push: `gcloud builds submit --tag gcr.io/$PROJECT_ID/litellm-proxy`
2) Deploy: `gcloud run deploy litellm-proxy --image gcr.io/$PROJECT_ID/litellm-proxy --region $REGION --allow-unauthenticated=false --set-env-vars OPENAI_API_KEY=...,PROXY_GATEWAY_TOKEN=...`
3) Tune autoscaling: `--concurrency`, `--min-instances`, `--max-instances`.
4) Observability: create log-based metrics for tokens and cost; add dashboards/alerts.

## Observability defaults
- Logs: JSON to stdout -> Cloud Logging.
- Metrics: derive via log-based metrics (tokens, cost, latency, errors).
- Dashboards/alerts: Cloud Monitoring (samples in `docs/deployment.md`).

## Stripe Billing
- Keep your own tenant table with `customer_id` and `subscription_item_id`.
- Post usage to Stripe per request/batch; see `docs/stripe-billing.md`.

