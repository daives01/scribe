"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "Scribe"
    debug: bool = True

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 1 week

    # Database
    database_url: str = "sqlite:///./scribe.db"

    # Ollama defaults (per-user overrides in UserSettings)
    default_ollama_url: str = "http://localhost:11434"
    default_ollama_model: str = "qwen3:4b-instruct"
    embedding_model: str = "nomic-embed-text"

    # Whisper
    whisper_model: str = "small"

    # Base URL for notifications (used for clickable HA notifications)
    base_url: str = "http://localhost:8000"


settings = Settings()
