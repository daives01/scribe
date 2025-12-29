"""Authentication web routes."""

from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import select

from app.api.deps import SessionDep
from app.models.user import User, UserSettings
from app.utils.auth import get_password_hash, verify_password

from . import (
    create_auth_response,
    get_current_user_from_cookie,
    require_user_id,
    router,
    templates,
)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None):
    """Render login page."""
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error, "current_user": None},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    session: SessionDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """Handle login form submission."""
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
                "current_user": None,
            },
        )

    user_id = require_user_id(user)
    return create_auth_response(user_id)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str | None = None):
    """Render register page."""
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": error, "current_user": None},
    )


@router.post("/register")
async def register_submit(
    request: Request,
    session: SessionDep,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """Handle register form submission."""
    if session.exec(select(User).where(User.username == username)).first():
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Username already taken",
                "current_user": None,
            },
        )

    user = User(username=username, hashed_password=get_password_hash(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = require_user_id(user)

    settings = UserSettings(user_id=user_id)
    session.add(settings)
    session.commit()

    return create_auth_response(user_id)


@router.get("/logout")
async def logout():
    """Log out and clear cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

