"""Prometheus metrics registry for the bsopt platform."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Pricing ──────────────────────────────────────────────────────
PRICE_COMPUTATIONS_TOTAL = Counter(
    "bsopt_price_computations_total",
    "Total number of pricing computations.",
    ["method_type", "option_type", "converged"],
)
PRICE_DURATION_SECONDS = Histogram(
    "bsopt_price_computation_duration_seconds",
    "Latency of pricing computations in seconds.",
    ["method_type"],
    buckets=[0.0001, 0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0],
)
PRICE_MAPE_GAUGE = Gauge(
    "bsopt_price_mape_percent",
    "Mean Absolute Percentage Error for pricing methods.",
    ["method_type"],
)

# ── NeonDB ────────────────────────────────────────────────────────
NEON_QUERY_DURATION = Histogram(
    "bsopt_neondb_query_duration_seconds",
    "NeonDB query duration in seconds.",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)
NEON_ERRORS_TOTAL = Counter(
    "bsopt_neondb_errors_total", "Total number of NeonDB errors.", ["operation"]
)
NEON_POOL_SIZE = Gauge("bsopt_neondb_pool_size", "Max pool connections.")
NEON_POOL_IDLE = Gauge("bsopt_neondb_pool_idle", "Idle pool connections.")

# ── Redis ─────────────────────────────────────────────────────────
REDIS_CACHE_HITS = Counter(
    "bsopt_redis_cache_hits_total", "Total number of Redis cache hits.", ["endpoint"]
)
REDIS_CACHE_MISSES = Counter(
    "bsopt_redis_cache_misses_total", "Total number of Redis cache misses.", ["endpoint"]
)

# ── RabbitMQ ──────────────────────────────────────────────────────
RABBITMQ_PUBLISHED = Counter(
    "bsopt_rabbitmq_tasks_published_total", "Total tasks published to RabbitMQ.", ["queue"]
)
RABBITMQ_CONSUMED = Counter(
    "bsopt_rabbitmq_tasks_consumed_total",
    "Total tasks consumed from RabbitMQ.",
    ["queue", "status"],
)

# ── MinIO ────────────────────────────────────────────────────────
MINIO_UPLOADS_TOTAL = Counter(
    "bsopt_minio_uploads_total", "Total number of uploads to MinIO.", ["bucket"]
)

# ── Scrapers ──────────────────────────────────────────────────────
SCRAPE_RUNS_TOTAL = Counter(
    "bsopt_scrape_runs_total", "Total number of scraper runs.", ["market", "status"]
)
SCRAPE_ROWS_INSERTED = Gauge(
    "bsopt_scrape_rows_inserted", "Number of rows inserted by scrapers.", ["market"]
)
SCRAPE_DURATION = Histogram(
    "bsopt_scrape_duration_seconds",
    "Scraper run duration in seconds.",
    ["market"],
    buckets=[5, 15, 30, 60, 120, 300, 600],
)
SCRAPE_ERRORS_TOTAL = Counter(
    "bsopt_scrape_errors_total", "Total number of scraper errors.", ["market", "error_type"]
)

# ── MLOps ────────────────────────────────────────────────────────
MLFLOW_RUNS_TOTAL = Counter(
    "bsopt_mlflow_runs_total", "Total number of MLflow runs.", ["experiment", "status"]
)
RAY_TASKS_SUBMITTED = Counter(
    "bsopt_ray_tasks_submitted_total", "Total Ray tasks submitted.", ["task_type"]
)
RAY_TASKS_COMPLETED = Counter(
    "bsopt_ray_tasks_completed_total", "Total Ray tasks completed.", ["task_type", "status"]
)
RAY_CLUSTER_CPUS = Gauge("bsopt_ray_cluster_cpus", "Ray cluster available CPUs.")

# ── Watchdog ──────────────────────────────────────────────────────
WATCHDOG_FILES_DETECTED = Counter(
    "bsopt_watchdog_files_detected_total",
    "Total files detected by Watchdog.",
    ["market", "extension"],
)

# ── WebSocket ─────────────────────────────────────────────────────
WS_CONNECTIONS_ACTIVE = Gauge(
    "bsopt_ws_connections_active", "Active WebSocket connections.", ["channel"]
)

# ── Notifications ────────────────────────────────────────────────
NOTIFICATIONS_SENT = Counter(
    "bsopt_notifications_sent_total", "Total notifications sent.", ["channel", "severity"]
)
