"""Page routes."""

from fastapi import Cookie, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import SessionDep, get_user_settings
from app.utils import get_custom_tags

from . import get_current_user_from_cookie, router, templates


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Render home page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "home.html", {"request": request, "current_user": user}
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Render settings page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_settings = get_user_settings(session, user)
    custom_tags = get_custom_tags(user_settings.custom_tags)

    server_url = str(request.base_url).rstrip("/")

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": user,
            "api_token": user.api_token,
            "server_url": server_url,
            "settings": {
                "ollama_url": user_settings.ollama_url,
                "ollama_model": user_settings.ollama_model,
                "ollama_embedding_model": user_settings.ollama_embedding_model,
                "ollama_api_key": user_settings.ollama_api_key,
                "custom_tags": custom_tags,
                "homeassistant_url": user_settings.homeassistant_url,
                "homeassistant_token": user_settings.homeassistant_token,
                "homeassistant_device": user_settings.homeassistant_device,
            },
        },
    )

