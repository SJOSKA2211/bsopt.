-- migrations/001_initial_schema.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    role TEXT CHECK (role IN ('researcher', 'admin')),
    notification_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS option_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    underlying_price FLOAT8 NOT NULL CHECK (underlying_price > 0),
    strike_price FLOAT8 NOT NULL CHECK (strike_price > 0),
    time_to_expiry FLOAT8 NOT NULL CHECK (time_to_expiry > 0),
    volatility FLOAT8 NOT NULL CHECK (volatility > 0),
    risk_free_rate FLOAT8 NOT NULL CHECK (risk_free_rate >= 0),
    option_type TEXT CHECK (option_type IN ('call', 'put')),
    exercise_type TEXT DEFAULT 'european' CHECK (exercise_type IN ('european', 'american')),
    market_source TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(underlying_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type, exercise_type, market_source)
);

CREATE TABLE IF NOT EXISTS method_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    option_id UUID NOT NULL REFERENCES option_parameters(id) ON DELETE CASCADE,
    method_type TEXT NOT NULL,
    parameter_set JSONB,
    parameter_hash TEXT NOT NULL,
    computed_price FLOAT8 NOT NULL,
    exec_seconds FLOAT8,
    converged BOOL,
    replications INT4,
    mlflow_run_id TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(option_id, method_type, parameter_hash)
);
CREATE INDEX IF NOT EXISTS idx_method_results_params ON method_results USING GIN (parameter_set);

CREATE TABLE IF NOT EXISTS market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    option_id UUID NOT NULL REFERENCES option_parameters(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    bid FLOAT8,
    ask FLOAT8,
    mid_price FLOAT8 GENERATED ALWAYS AS ((bid + ask) / 2) STORED,
    volume INT4,
    oi INT4,
    implied_vol FLOAT8,
    data_source TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(option_id, trade_date)
);

CREATE TABLE IF NOT EXISTS validation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    option_id UUID NOT NULL REFERENCES option_parameters(id),
    method_result_id UUID NOT NULL REFERENCES method_results(id),
    absolute_error FLOAT8,
    mape FLOAT8,
    market_deviation FLOAT8,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(option_id, method_result_id)
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market TEXT NOT NULL,
    scraper_class TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    rows_inserted INT4 DEFAULT 0,
    status TEXT CHECK (status IN ('running', 'success', 'failed')),
    triggered_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_affected INT4 DEFAULT 0,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scrape_run_id UUID REFERENCES scrape_runs(id),
    url TEXT,
    error_type TEXT,
    error_message TEXT,
    attempt INT4 DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'error')),
    channel TEXT CHECK (channel IN ('email', 'websocket', 'push')),
    read BOOL DEFAULT FALSE,
    action_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    mlflow_experiment_id TEXT,
    ray_job_id TEXT,
    status TEXT,
    hyperparams JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE UNIQUE NOT NULL,
    features JSONB NOT NULL,
    option_count INT4,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
