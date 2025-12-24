# LiteLLM Proxy on Google Cloud – Architecture

## Goals
- Serve AI requests through a LiteLLM proxy with strong isolation per tenant.
- Autoscale transparently on Google Cloud Run.
- First-party observability with Cloud Logging/Monitoring (tokens, cost, latency, errors).
- Stripe Billing integration for metered or seat-based plans.
- Minimal operational burden; secrets live in Secret Manager.

## Components
- **LiteLLM Proxy (Cloud Run)**: Stateless container running `litellm --config config.yaml`; scales to zero and up automatically.
- **Auth**: Proxy bearer token (or IAM) to gate access; per-tenant tokens optional at app layer.
- **Model providers**: OpenAI/Anthropic/etc. keys injected via env/Secret Manager.
- **Observability**:
  - Structured JSON logs -> Cloud Logging.
  - Log-based metrics in Cloud Monitoring for tokens, cost, latency, errors.
  - Dashboards/alerts in Cloud Monitoring; optional Grafana via Monitoring data source.
  - Optional export to BigQuery for deep analysis / retention.
- **Billing**:
  - Stripe Billing for subscriptions (flat + metered).
  - Usage records posted per tenant from app/proxy callback.
  - Customer/subscription metadata stored in your app DB; Stripe is the billing ledger.
- **Networking/Security**:
  - Cloud Run private or behind HTTPS LB + Cloud Armor.
  - Secret Manager for API keys; Workload Identity for provider keys where supported.
  - VPC connector only if models require egress controls (generally not needed for public APIs).

## Request Flow
1) Client calls your gateway → authenticated request to LiteLLM proxy (`/v1/chat/completions` etc.).
2) Proxy forwards to provider; retries/timeouts via LiteLLM router settings.
3) Callback emits structured log (tenant, model, tokens, cost, latency, status) to stdout → Cloud Logging.
4) Log-based metrics aggregate token burn and cost; dashboards and alerts trigger from these metrics.
5) App (or callback) also posts metered usage to Stripe for the customer’s subscription item; Stripe invoices on its schedule.

## Scaling Model
- Cloud Run autoscaling on concurrency; tune `min-instances` for cold start avoidance and `max-instances` for budget caps.
- Concurrency 10–20 is a good starting point; lower for stricter latency SLOs.
- CPU always allocated optional; keep on if background tasks are needed.

## Data Model (minimal)
- `tenant_id` (string), `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `latency_ms`, `status`, `cost_usd`, `request_id`, `timestamp`.
- Optional: `customer_id` (Stripe), `subscription_item_id`, `trace_id`.

## Resilience & Limits
- LiteLLM retries configurable; set timeouts to avoid stuck requests.
- Idempotency keys from clients recommended for higher-level operations.
- Budget guardrails: app-side quotas per tenant; Stripe handles invoicing but not live enforcement.

## Security Considerations
- Do not expose proxy publicly without auth; prefer bearer gateway token or IAM.
- Encrypt secrets; prefer Secret Manager → environment variables; rotate keys.
- Verify Stripe webhook signatures; use idempotency keys for usage writes.


