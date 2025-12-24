-- Table for customer billing information
CREATE TABLE IF NOT EXISTS customers (
    tenant_id TEXT PRIMARY KEY, -- Corresponds to the LiteLLM token/user ID
    stripe_customer_id TEXT UNIQUE,
    balance_usd NUMERIC(10, 4) DEFAULT 0.0000,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for billing transactions (credits and debits)
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT REFERENCES customers(tenant_id),
    stripe_charge_id TEXT, -- Null for usage debits
    amount_usd NUMERIC(10, 4), -- Positive for credit, Negative for debit
    balance_after NUMERIC(10, 4),
    type TEXT NOT NULL, -- 'credit', 'debit_usage', 'adjustment'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_tenant ON transactions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions (created_at);
