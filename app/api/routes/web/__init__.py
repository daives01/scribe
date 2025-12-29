"""Web routes for HTMX frontend - package exports."""

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app.models.user import User
from app.utils.auth import create_access_token, decode_access_token
from app.utils.exceptions import AuthenticationError

router = APIRouter(tags=["web"])
logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")


def from_json(value):
    """Parse JSON string to Python object."""
    try:
        return json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return value


templates.env.filters["from_json"] = from_json


async def get_current_user_from_cookie(
    _request: Request,
    session: Session,
    access_token: str | None,
) -> User | None:
    """Get current user from cookie token."""
    if not access_token:
        return None

    try:
        token_data = decode_access_token(access_token)
        if token_data.user_id is None:
            return None
        user = session.get(User, token_data.user_id)
        return user
    except AuthenticationError:
        return None


def require_user_id(user: User | None) -> int:
    """
    Get user ID from user object, raising an error if user is None or ID is missing.

    Args:
        user: User object (may be None)

    Returns:
        User ID as integer

    Raises:
        ValueError: If user is None or user.id is None
    """
    if user is None:
        raise ValueError("User is not authenticated")
    if user.id is None:
        raise ValueError("User ID is missing")
    return user.id


def create_auth_response(user_id: int, redirect_url: str = "/") -> RedirectResponse:
    """Create a redirect response with authentication cookie."""
    from app.config import settings

    access_token = create_access_token(user_id)
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.debug,  # Secure cookies in production (HTTPS only)
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


from . import auth, notes, pages, search, settings  # noqa: F401
