"""Authentication schemas."""

from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login (OAuth2 compatible)."""

    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    user_id: int | None = None


class ApiTokenResponse(BaseModel):
    """API token response for mobile/Siri access."""

    api_token: str
    message: str = "Use this token in the Authorization header as 'Bearer <token>'"
