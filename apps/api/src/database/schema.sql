-- Schema for bsopt research platform

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS option_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    underlying_price DECIMAL NOT NULL,
    strike_price DECIMAL NOT NULL,
    time_to_expiry DECIMAL NOT NULL,
    volatility DECIMAL NOT NULL,
    risk_free_rate DECIMAL NOT NULL,
    option_type TEXT NOT NULL,
    market_source TEXT NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(underlying_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type, market_source)
);

CREATE TABLE IF NOT EXISTS method_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    option_id UUID REFERENCES option_parameters(id),
    method_type TEXT NOT NULL,
    computed_price DECIMAL NOT NULL,
    exec_seconds DECIMAL NOT NULL,
    converged BOOLEAN DEFAULT TRUE,
    parameter_set JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    option_id UUID REFERENCES option_parameters(id),
    trade_date DATE NOT NULL,
    bid DECIMAL,
    ask DECIMAL,
    volume INTEGER,
    oi INTEGER,
    data_source TEXT NOT NULL,
    implied_vol DECIMAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(option_id, trade_date)
);

CREATE TABLE IF NOT EXISTS validation_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    method_result_id UUID REFERENCES method_results(id),
    absolute_error DECIMAL NOT NULL,
    relative_error DECIMAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market TEXT NOT NULL,
    scraper_class TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    row_counts INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id TEXT NOT NULL,
    experiment_name TEXT NOT NULL,
    params JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    features JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_run_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_affected INTEGER DEFAULT 0,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
