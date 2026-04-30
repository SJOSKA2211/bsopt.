"""Configuration management for bsopt via pydantic-settings."""
from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """System-wide settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # NeonDB
    neon_connection_string: str
    neon_api_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_password: str

    # RabbitMQ
    rabbitmq_url: str
    rabbitmq_user: str
    rabbitmq_password: str

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: str
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

    # Auth
    nextauth_secret: str
    gh_client_id: str
    gh_client_secret: str
    gh_token: str
    gh_deploy_hook: str
    gh_packages_token: str
    google_client_id: str
    google_client_secret: str

    # Email
    resend_api_key: str

    # Environment
    env: str = "production"

@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings() # type: ignore
