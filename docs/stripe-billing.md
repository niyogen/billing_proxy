# Stripe Billing Integration Guide

Goal: keep Stripe as billing ledger while the proxy/app meters usage per tenant.

## Data you store
- `tenant_id`
- `stripe_customer_id`
- `subscription_item_id` for the metered price (one per metered dimension)
- Optional: seat counts, plan type, soft/hard quota limits

## Stripe setup
1) Create **Product** and **Price** (metered) for "API tokens" or "requests".
   - Price type: metered
   - Aggregate: sum during period
   - Unit: pick one (tokens or requests) and stick to it.
2) (Optional) Add a seat/flat price for base subscription.
3) Create **Customer** when user/tenant signs up.
4) Create **Subscription** with the metered price; capture `subscription_item_id`.
5) Enable Customer Portal for self-serve payment methods and plan changes.

## Posting usage
- For each billable request (or batch), call `usage_records.create`:
```python
import stripe, time
stripe.api_key = "<STRIPE_SECRET_KEY>"

def report_usage(subscription_item_id: str, quantity: int):
    stripe.UsageRecord.create(
        subscription_item=subscription_item_id,
        quantity=quantity,
        timestamp=int(time.time()),
        action="increment",
    )
```
- Batch to reduce API calls (e.g., every 1–5 minutes per tenant).
- Use idempotency keys if retrying batches to avoid double counting.

## Mapping from proxy to Stripe
- Include `tenant_id` in LiteLLM request metadata.
- The callback (or your gateway) resolves `tenant_id -> subscription_item_id`.
- Quantity = chosen unit (e.g., `total_tokens` or `1` per request).
- Keep your own DB/warehouse as audit source; Stripe is billing source.

## Webhooks to handle
- `invoice.upcoming`: warn about expected charges; show usage in-app.
- `invoice.payment_failed`: pause or downgrade access; ask for new payment method.
- `customer.subscription.updated` / `...deleted`: update entitlements locally.
- Always verify webhook signatures and use idempotency for side effects.

## Quotas and enforcement
- Soft limits: warn when approaching plan quota (from your DB usage).
- Hard limits: block or degrade requests when exceeding plan; Stripe does not enforce live quotas.

## Cost vs. price
- LiteLLM can emit `cost_usd` per request (provider cost). Stripe price is what you charge. Track both:
  - Provider cost: from LiteLLM log callback / metadata.
  - Customer price: defined in Stripe; use reports/invoices there.

## Minimal flow
1) Tenant signup -> create Stripe customer + subscription (store ids).
2) Requests flow through proxy; callback logs usage and batches to Stripe.
3) Stripe invoices automatically; your webhook updates access state.

