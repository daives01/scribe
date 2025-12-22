"""Authentication endpoints."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.api.deps import CurrentUserDep, SessionDep
from app.models.user import User, UserSettings
from app.schemas.auth import ApiTokenResponse, Token, UserCreate, UserResponse
from app.services.auth_service import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, session: SessionDep) -> Token:
    """
    Register a new user account.

    Returns JWT token on successful registration.
    """
    # Check if username already exists
    statement = select(User).where(User.username == user_data.username)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Create default settings for the user
    settings = UserSettings(user_id=user.id)
    session.add(settings)
    session.commit()

    # Generate token
    access_token = create_access_token(user.id)
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> Token:
    """
    Login with username and password.

    Returns JWT token on successful authentication.
    """
    # Find user by username
    statement = select(User).where(User.username == form_data.username)
    user = session.exec(statement).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token = create_access_token(user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: CurrentUserDep) -> UserResponse:
    """
    Get the current authenticated user's information.
    """
    return UserResponse.model_validate(current_user)


@router.post("/api-token", response_model=ApiTokenResponse)
def generate_api_token(current_user: CurrentUserDep, session: SessionDep) -> ApiTokenResponse:
    """
    Generate a new long-lived API token for mobile/Siri access.

    This token never expires and can be used in the Authorization header.
    Generating a new token will invalidate the previous one.
    """
    # Generate a new secure token
    api_token = secrets.token_urlsafe(32)

    # Update user's API token
    current_user.api_token = api_token
    session.add(current_user)
    session.commit()

    return ApiTokenResponse(api_token=api_token)


@router.delete("/api-token", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_token(current_user: CurrentUserDep, session: SessionDep) -> None:
    """
    Revoke the current API token.
    """
    current_user.api_token = None
    session.add(current_user)
    session.commit()
