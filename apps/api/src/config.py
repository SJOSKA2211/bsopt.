"""Configuration management using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """System settings for the bsopt platform."""

    # NeonDB (PostgreSQL)
    neon_connection_string: str = (
        "postgresql://neondb_owner:npg_imMo5wPNOUX8@ep-wild-sea-anid9s9s-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    neon_api_url: str = (
        "https://ep-wild-sea-anid9s9s.apirest.c-6.us-east-1.aws.neon.tech/neondb/rest/v1"
    )

    # Redis
    redis_url: str = "redis://redis:7379/0"
    redis_password: str = "placeholder_redis_pass_20_chars"

    # RabbitMQ
    rabbitmq_url: str = "amqp://bsopt_user:placeholder_rabbit_pass_20@rabbitmq:5672/"
    rabbitmq_user: str = "bsopt_user"
    rabbitmq_password: str = "placeholder_rabbit_pass_20"

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
    watchdog_watch_dir: str = "/app/data/watch"

    # Auth & API
    nextauth_secret: str = "placeholder_nextauth_secret_32_chars"
    nextauth_url: str = "https://bsopt.vercel.app"
    gh_client_id: str = "placeholder_gh_id"
    gh_client_secret: str = "placeholder_gh_secret"
    gh_token: str = "placeholder_gh_token"
    gh_deploy_hook: str = "placeholder_gh_hook"
    gh_packages_token: str = "placeholder_gh_pkg_token"
    google_client_id: str = "placeholder_google_id"
    google_client_secret: str = "placeholder_google_secret"
    resend_api_key: str = "placeholder_resend_key"

    # Public URLs
    next_public_ws_url: str = "wss://api.bsopt.example.com/ws"
    next_public_api_url: str = "https://api.bsopt.example.com"

    # Environment
    env: str = "production"
    debug: bool = False
    enable_compression: bool = True

    # Web Push VAPID keys
    gh_vapid_private_key: str | None = None
    gh_vapid_public_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
