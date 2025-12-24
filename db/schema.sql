-- Table for LiteLLM proxy usage logs
CREATE TABLE IF NOT EXISTS litellm_usage (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tenant_id TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER,
    status INTEGER,
    cost_usd NUMERIC(12,6),
    request_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_litellm_usage_created_at ON litellm_usage (created_at);
CREATE INDEX IF NOT EXISTS idx_litellm_usage_tenant ON litellm_usage (tenant_id);
CREATE INDEX IF NOT EXISTS idx_litellm_usage_request_id ON litellm_usage (request_id);


