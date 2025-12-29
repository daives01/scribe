"""API dependencies for dependency injection."""

import json
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User, UserSettings
from app.utils import get_custom_tags
from app.utils.auth import decode_access_token
from app.utils.exceptions import AuthenticationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    yield from get_session()


SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    session: SessionDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """
    Get the current authenticated user from JWT token, cookie, or API token.

    Supports:
    - JWT tokens from OAuth2 flow
    - JWT tokens from 'access_token' cookie
    - Long-lived API tokens (for mobile/Siri)

    Args:
        session: Database session
        token: JWT token from OAuth2
        request: FastAPI Request object
        authorization: Raw Authorization header (for API token fallback)

    Returns:
        Authenticated User instance

    Raises:
        HTTPException: If authentication fails
    """
    # Try JWT token first (Header)
    if token:
        try:
            token_data = decode_access_token(token)
            if token_data.user_id is not None:
                user = session.get(User, token_data.user_id)
                if user:
                    return user
        except AuthenticationError:
            pass

    # Try JWT token from Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        try:
            token_data = decode_access_token(cookie_token)
            if token_data.user_id is not None:
                user = session.get(User, token_data.user_id)
                if user:
                    return user
        except AuthenticationError:
            pass

    # Try API token from Authorization header
    if authorization and authorization.startswith("Bearer "):
        api_token = authorization.removeprefix("Bearer ").strip()

        # Look up user by API token
        statement = select(User).where(User.api_token == api_token)
        user = session.exec(statement).first()
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_user_id(current_user: CurrentUserDep) -> int:
    """Get the current user's ID, asserting it's not None."""
    assert current_user.id is not None
    return current_user.id


CurrentUserIdDep = Annotated[int, Depends(get_current_user_id)]


def get_user_settings(
    session: SessionDep, current_user: CurrentUserDep
) -> UserSettings:
    """
    Get the current user's settings.

    Args:
        session: Database session
        current_user: Authenticated user

    Returns:
        UserSettings instance (creates default if none exists)
    """
    assert current_user.id is not None
    statement = select(UserSettings).where(UserSettings.user_id == current_user.id)
    settings = session.exec(statement).first()

    if not settings:
        # Create default settings for user
        settings = UserSettings(user_id=current_user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    return settings


UserSettingsDep = Annotated[UserSettings, Depends(get_user_settings)]


def get_user_tags(user_settings: UserSettingsDep) -> list[str]:
    """
    Get the current user's custom tags.

    Args:
        user_settings: User's settings

    Returns:
        List of tag strings
    """
    return get_custom_tags(user_settings.custom_tags)


UserTagsDep = Annotated[list[str], Depends(get_user_tags)]


def _update_user_settings(
    user_settings: UserSettings,
    ollama_url: str | None = None,
    ollama_model: str | None = None,
    ollama_embedding_model: str | None = None,
    ollama_api_key: str | None = None,
    custom_tags: list[str] | None = None,
    homeassistant_url: str | None = None,
    homeassistant_token: str | None = None,
    homeassistant_device: str | None = None,
) -> None:
    """
    Update user settings with provided values.

    Args:
        user_settings: UserSettings instance to update
        ollama_url: Optional Ollama URL
        ollama_model: Optional Ollama model name
        ollama_embedding_model: Optional embedding model name
        ollama_api_key: Optional API key
        custom_tags: Optional list of custom tags
        homeassistant_url: Optional Home Assistant URL
        homeassistant_token: Optional Home Assistant token
        homeassistant_device: Optional Home Assistant device name
    """
    if ollama_url is not None:
        user_settings.ollama_url = ollama_url

    if ollama_model is not None:
        user_settings.ollama_model = ollama_model

    if ollama_embedding_model is not None:
        user_settings.ollama_embedding_model = ollama_embedding_model

    if ollama_api_key is not None:
        user_settings.ollama_api_key = ollama_api_key

    if custom_tags is not None:
        user_settings.custom_tags = json.dumps(custom_tags)

    if homeassistant_url is not None:
        user_settings.homeassistant_url = homeassistant_url

    if homeassistant_token is not None:
        user_settings.homeassistant_token = homeassistant_token

    if homeassistant_device is not None:
        user_settings.homeassistant_device = homeassistant_device
