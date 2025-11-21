from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "dev"
    frontend_url: str = "http://localhost:3000"
    extra_cors_origins: str = ""
    upload_dir: str = "/tmp/inkami/uploads"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/inkami"
    redis_url: str = "redis://localhost:6379/0"
    job_queue_name: str = "inkami"

    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "inkami"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    elevenlabs_api_key: str | None = None
    deepsick_api_key: str | None = None
    deepseek_api_key: str | None = None
    openai_api_key: str | None = None
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    google_application_credentials: str | None = None
    tts_provider_priority: str = "openai"
    force_https_assets: bool = True
    enable_local_detector: bool = True
    vision_single_pass: bool = False
    job_timeout_seconds: int = 900


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

