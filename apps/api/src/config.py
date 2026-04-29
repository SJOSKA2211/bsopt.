"""Configuration management using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings for bsopt."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    debug: bool = False

    # NeonDB
    neon_connection_string: str = (
        "postgresql://neondb_owner:npg_imMo5wPNOUX8@ep-wild-sea-anid9s9s-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    neon_api_url: str = (
        "https://ep-wild-sea-anid9s9s.apirest.c-6.us-east-1.aws.neon.tech/neondb/rest/v1"
    )

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_password: str = "admin"

    # RabbitMQ
    rabbitmq_url: str = "amqp://admin:admin@rabbitmq:5672/"
    rabbitmq_user: str = "admin"
    rabbitmq_password: str = "admin"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_exports: str = "bsopt-exports"
    minio_bucket_models: str = "bsopt-models"
    minio_bucket_scraper: str = "bsopt-scraper"

    # Ray
    ray_address: str = "ray://ray-head:10001"
    ray_dashboard_port: int = 8265

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_artifact_root: str = "s3://bsopt-models"
    mlflow_s3_endpoint_url: str = "http://minio:9000"

    # Watchdog
    watchdog_watch_dir: str = "data/watch"

    # Grafana
    grafana_admin_password: str = "placeholder16chars"

    # Auth & Frontend URLs (Secrets with GH_ prefix as per prompt)
    nextauth_secret: str = "placeholder32charsrandomstring!!!"
    nextauth_url: str = "https://bsopt.vercel.app"
    gh_client_id: str | None = None
    gh_client_secret: str | None = None
    gh_token: str | None = None
    gh_deploy_hook: str | None = None
    gh_packages_token: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    resend_api_key: str | None = None
    gh_vapid_private_key: str | None = None
    gh_vapid_public_key: str | None = None
    next_public_ws_url: str = "wss://api.bsopt.example.com/ws"
    next_public_api_url: str = "https://api.bsopt.example.com"

    # Optimization
    enable_compression: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
