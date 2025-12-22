"""User settings schemas."""

from pydantic import BaseModel


class UserSettingsResponse(BaseModel):
    """Schema for user settings response."""

    ollama_url: str
    ollama_model: str
    ollama_embedding_model: str
    ollama_api_key: str | None
    custom_tags: list[str]
    homeassistant_url: str | None
    homeassistant_token: str | None
    homeassistant_device: str | None

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""

    ollama_url: str | None = None
    ollama_model: str | None = None
    ollama_embedding_model: str | None = None
    ollama_api_key: str | None = None
    custom_tags: list[str] | None = None
    homeassistant_url: str | None = None
    homeassistant_token: str | None = None
    homeassistant_device: str | None = None


class ModelsResponse(BaseModel):
    """Schema for available models response."""

    models: list[str]
