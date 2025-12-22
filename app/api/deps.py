"""API dependencies for dependency injection."""

import json
from collections.abc import Generator
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User, UserSettings
from app.services.auth_service import decode_access_token
from app.utils.exceptions import AuthenticationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency."""
    yield from get_session()


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[Optional[str], Depends(oauth2_scheme)]


def get_current_user(
    session: SessionDep,
    token: TokenDep,
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
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
        api_token = authorization[7:]  # Remove "Bearer " prefix

        # Look up user by API token
        statement = select(User).where(User.api_token == api_token)
        user = session.exec(statement).first()
        if user:
            return user

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_user_settings(session: SessionDep, current_user: CurrentUserDep) -> UserSettings:
    """
    Get the current user's settings.

    Args:
        session: Database session
        current_user: Authenticated user

    Returns:
        UserSettings instance (creates default if none exists)
    """
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
    try:
        return json.loads(user_settings.custom_tags)
    except json.JSONDecodeError:
        return ["Idea", "Todo", "Work", "Personal", "Reference"]


UserTagsDep = Annotated[list[str], Depends(get_user_tags)]
