"""User settings endpoints."""

import json

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, SessionDep, UserSettingsDep
from app.schemas.settings import (
    ModelsResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from app.services.ollama_service import get_ollama_service
from app.utils import get_custom_tags

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
def get_settings(user_settings: UserSettingsDep) -> UserSettingsResponse:
    """
    Get the current user's settings.
    """
    custom_tags = get_custom_tags(user_settings.custom_tags)

    return UserSettingsResponse(
        ollama_url=user_settings.ollama_url,
        ollama_model=user_settings.ollama_model,
        ollama_embedding_model=user_settings.ollama_embedding_model,
        ollama_api_key=user_settings.ollama_api_key,
        custom_tags=custom_tags,
        homeassistant_url=user_settings.homeassistant_url,
        homeassistant_token=user_settings.homeassistant_token,
        homeassistant_device=user_settings.homeassistant_device,
    )


@router.patch("", response_model=UserSettingsResponse)
def update_settings(
    update_data: UserSettingsUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
    user_settings: UserSettingsDep,
) -> UserSettingsResponse:
    """
    Update the current user's settings.
    """
    if update_data.ollama_url is not None:
        user_settings.ollama_url = update_data.ollama_url

    if update_data.ollama_model is not None:
        user_settings.ollama_model = update_data.ollama_model

    if update_data.ollama_embedding_model is not None:
        user_settings.ollama_embedding_model = update_data.ollama_embedding_model

    if update_data.ollama_api_key is not None:
        user_settings.ollama_api_key = update_data.ollama_api_key

    if update_data.custom_tags is not None:
        user_settings.custom_tags = json.dumps(update_data.custom_tags)

    if update_data.homeassistant_url is not None:
        user_settings.homeassistant_url = update_data.homeassistant_url

    if update_data.homeassistant_token is not None:
        user_settings.homeassistant_token = update_data.homeassistant_token

    if update_data.homeassistant_device is not None:
        user_settings.homeassistant_device = update_data.homeassistant_device

    session.add(user_settings)
    session.commit()
    session.refresh(user_settings)

    custom_tags = get_custom_tags(user_settings.custom_tags)

    return UserSettingsResponse(
        ollama_url=user_settings.ollama_url,
        ollama_model=user_settings.ollama_model,
        ollama_embedding_model=user_settings.ollama_embedding_model,
        ollama_api_key=user_settings.ollama_api_key,
        custom_tags=custom_tags,
        homeassistant_url=user_settings.homeassistant_url,
        homeassistant_token=user_settings.homeassistant_token,
        homeassistant_device=user_settings.homeassistant_device,
    )


@router.get("/models", response_model=ModelsResponse)
async def get_available_models(user_settings: UserSettingsDep) -> ModelsResponse:
    """
    Get list of available models from Ollama.
    """
    ollama = get_ollama_service(
        base_url=user_settings.ollama_url,
        api_key=user_settings.ollama_api_key,
    )
    models = await ollama.get_available_models()
    return ModelsResponse(models=models)
