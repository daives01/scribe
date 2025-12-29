"""Application configuration using Pydantic Settings."""

import logging
import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # CORS
    cors_origins: list[str] = ["*"]

    def __init__(self, **kwargs):
        """Initialize settings and validate production configuration."""
        super().__init__(**kwargs)
        self._validate_production_settings()

    def _validate_production_settings(self) -> None:
        """Validate and warn about insecure production settings."""
        if not self.debug:
            # Production mode - check for insecure settings
            if self.secret_key == "change-me-in-production":
                warnings.warn(
                    "SECRET_KEY is set to default value. Change this in production!",
                    UserWarning,
                    stacklevel=2,
                )
                logger.warning(
                    "SECRET_KEY is set to default value. Change this in production!"
                )

            if "*" in self.cors_origins:
                warnings.warn(
                    "CORS is configured to allow all origins (*). Restrict this in production!",
                    UserWarning,
                    stacklevel=2,
                )
                logger.warning(
                    "CORS is configured to allow all origins (*). Restrict this in production!"
                )


settings = Settings()
