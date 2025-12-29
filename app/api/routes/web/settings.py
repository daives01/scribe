"""Settings web routes for HTMX frontend."""

import secrets
from typing import Annotated

from fastapi import Cookie, Form, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, _update_user_settings, get_user_settings
from app.services.ollama_service import OllamaService

from . import get_current_user_from_cookie, logger, router, templates


@router.get("/web/settings/models", response_class=HTMLResponse)
async def get_models(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    ollama_url: str | None = None,
):
    """Get available Ollama models as select options."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="<option>Please log in</option>")

    user_settings = get_user_settings(session, user)
    target_url = ollama_url or user_settings.ollama_url

    ollama = OllamaService(base_url=target_url, api_key=user_settings.ollama_api_key)

    try:
        models = await ollama.get_available_models()
        if not models:
            models = [user_settings.ollama_model]
    except Exception as e:
        logger.warning(f"Failed to fetch models from Ollama: {e}")
        models = [user_settings.ollama_model]

    options = []
    if user_settings.ollama_model not in models:
        models.insert(0, user_settings.ollama_model)

    for model in models:
        selected = "selected" if model == user_settings.ollama_model else ""
        options.append(f'<option value="{model}" {selected}>{model}</option>')

    return HTMLResponse(content="\n".join(options))


@router.get("/web/settings/status", response_class=HTMLResponse)
async def get_connection_status(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    ollama_url: str | None = None,
):
    """Get Ollama connection status."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="<p>Please log in</p>")

    user_settings = get_user_settings(session, user)
    target_url = ollama_url or user_settings.ollama_url

    ollama = OllamaService(base_url=target_url, api_key=user_settings.ollama_api_key)
    connected = await ollama.check_connection()

    if connected:
        return HTMLResponse(
            content="""
            <div class="flex items-center gap-3">
                <div class="p-2 rounded-full" style="background-color: rgb(16 185 129 / 0.15);">
                    <svg class="w-5 h-5" style="color: var(--color-success);" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <div>
                    <p class="font-medium" style="color: var(--color-success);">Connected to Ollama</p>
                    <p class="text-sm" style="color: var(--color-text-secondary);">Your AI backend is ready</p>
                </div>
            </div>
            """
        )
    else:
        return HTMLResponse(
            content="""
            <div class="flex items-center gap-3">
                <div class="p-2 rounded-full" style="background-color: rgb(239 68 68 / 0.15);">
                    <svg class="w-5 h-5" style="color: var(--color-error);" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </div>
                <div>
                    <p class="font-medium" style="color: var(--color-error);">Cannot connect to Ollama</p>
                    <p class="text-sm" style="color: var(--color-text-secondary);">Make sure Ollama is running at the configured URL</p>
                </div>
            </div>
            """
        )


@router.patch("/web/settings", response_class=HTMLResponse)
async def update_settings_web(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    ollama_url: Annotated[str | None, Form()] = None,
    ollama_model: Annotated[str | None, Form()] = None,
    ollama_embedding_model: Annotated[str | None, Form()] = None,
    ollama_api_key: Annotated[str | None, Form()] = None,
    custom_tags: Annotated[str | None, Form()] = None,
    homeassistant_url: Annotated[str | None, Form()] = None,
    homeassistant_token: Annotated[str | None, Form()] = None,
    homeassistant_device: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """
    Update user settings (HTMX Form).

    Accepts form data, processes tags, and updates the database.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings(session, user)

    custom_tags_list: list[str] | None = None
    if custom_tags is not None:
        custom_tags_list = [
            tag.strip() for tag in custom_tags.split(",") if tag.strip()
        ]

    _update_user_settings(
        user_settings,
        ollama_url=ollama_url if ollama_url else None,
        ollama_model=ollama_model if ollama_model else None,
        ollama_embedding_model=(
            ollama_embedding_model if ollama_embedding_model else None
        ),
        ollama_api_key=ollama_api_key.strip() if ollama_api_key else None,
        custom_tags=custom_tags_list,
        homeassistant_url=homeassistant_url.strip() if homeassistant_url else None,
        homeassistant_token=(
            homeassistant_token.strip() if homeassistant_token else None
        ),
        homeassistant_device=(
            homeassistant_device.strip() if homeassistant_device else None
        ),
    )

    session.add(user_settings)
    session.commit()

    return HTMLResponse(content="", status_code=200)


@router.post("/web/api-token", response_class=HTMLResponse)
async def generate_api_token_web(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Generate a new API token (HTMX).

    Returns HTML for the updated API token section.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    api_token = secrets.token_urlsafe(32)

    user.api_token = api_token
    session.add(user)
    session.commit()

    html_content = f"""
    <div class="p-4 rounded-lg" style="background-color: var(--color-bg-tertiary);">
        <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium">Your API Token</span>
            <button hx-delete="/web/api-token" hx-target="#api-token-section" hx-swap="innerHTML"
                hx-confirm="Revoke this token? Any Siri shortcuts using it will stop working."
                class="text-xs px-2 py-1 rounded"
                style="color: var(--color-error); background-color: rgb(239 68 68 / 0.1);">
                Revoke
            </button>
        </div>
        <code class="block p-3 rounded text-sm break-all"
            style="background-color: var(--color-bg-primary);">{api_token}</code>
    </div>
    """
    return HTMLResponse(content=html_content)


@router.delete("/web/api-token", response_class=HTMLResponse)
async def revoke_api_token_web(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Revoke the current API token (HTMX).

    Returns HTML for the updated API token section (generate button).
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user.api_token = None
    session.add(user)
    session.commit()

    html_content = """
    <button hx-post="/web/api-token" hx-target="#api-token-section" hx-swap="innerHTML"
        class="w-full py-3 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
        style="background: linear-gradient(135deg, #FF6B6B, #FF8E53);">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
        Generate API Token
    </button>
    """
    return HTMLResponse(content=html_content)

