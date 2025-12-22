"""Web routes for HTMX frontend."""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.note import Note
from app.models.user import User, UserSettings
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.services.note_service import NoteService
from app.services.ollama_service import get_ollama_service
from app.utils.exceptions import AuthenticationError, NotFoundError

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")


# Custom Jinja2 filter
def from_json(value):
    """Parse JSON string to Python object."""
    try:
        return json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError:
        return value


templates.env.filters["from_json"] = from_json

# Type alias for session dependency
SessionDep = Annotated[Session, Depends(get_db)]


# ============= Cookie-based Auth Helpers =============


async def get_current_user_from_cookie(
    request: Request,
    session: Session,
    access_token: Optional[str],
) -> Optional[User]:
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


def get_user_settings_for_user(session: Session, user: User) -> UserSettings:
    """Get or create user settings."""
    statement = select(UserSettings).where(UserSettings.user_id == user.id)
    settings = session.exec(statement).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


# ============= Auth Page Routes =============


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
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
            {"request": request, "error": "Invalid username or password", "current_user": None},
        )

    access_token = create_access_token(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None):
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
            {"request": request, "error": "Username already taken", "current_user": None},
        )

    user = User(username=username, hashed_password=get_password_hash(password))
    session.add(user)
    session.commit()
    session.refresh(user)

    settings = UserSettings(user_id=user.id)
    session.add(settings)
    session.commit()

    access_token = create_access_token(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Log out and clear cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# ============= Page Routes =============


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Render home page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("home.html", {"request": request, "current_user": user})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Render settings page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_settings = get_user_settings_for_user(session, user)
    try:
        custom_tags = json.loads(user_settings.custom_tags)
    except (json.JSONDecodeError, TypeError):
        custom_tags = ["Idea", "Todo", "Work", "Personal", "Reference"]

    # Get server URL from request
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
                "ollama_api_key": user_settings.ollama_api_key,
                "custom_tags": custom_tags,
            },
        },
    )


# ============= API Token Routes =============


@router.post("/web/api-token", response_class=HTMLResponse)
async def generate_web_api_token(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Generate a new API token (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    # Generate new token
    import secrets
    api_token = secrets.token_urlsafe(32)
    user.api_token = api_token
    session.add(user)
    session.commit()
    session.refresh(user)

    return HTMLResponse(
        content=f"""
        <div class="p-4 rounded-lg" style="background-color: var(--color-bg-tertiary);">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium">Your API Token</span>
            <button
              hx-delete="/web/api-token"
              hx-target="#api-token-section"
              hx-swap="innerHTML"
              hx-confirm="Revoke this token? Any Siri shortcuts using it will stop working."
              class="text-xs px-2 py-1 rounded"
              style="color: var(--color-error); background-color: rgb(239 68 68 / 0.1);"
            >
              Revoke
            </button>
          </div>
          <code class="block p-3 rounded text-sm break-all" style="background-color: var(--color-bg-primary);">{api_token}</code>
        </div>
        """
    )


@router.delete("/web/api-token", response_class=HTMLResponse)
async def revoke_web_api_token(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Revoke the API token (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user.api_token = None
    session.add(user)
    session.commit()

    return HTMLResponse(
        content="""
        <button
          hx-post="/web/api-token"
          hx-target="#api-token-section"
          hx-swap="innerHTML"
          class="w-full py-3 rounded-lg font-medium text-white transition flex items-center justify-center gap-2"
          style="background: linear-gradient(135deg, #FF6B6B, #FF8E53);"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
          </svg>
          Generate API Token
        </button>
        """
    )


# ============= HTMX Partial Routes =============


@router.get("/web/notes/recent", response_class=HTMLResponse)
async def recent_notes(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
    limit: int = 12,
):
    """Get recent notes as HTML cards."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="<p>Please log in</p>", status_code=401)

    note_service = NoteService(session)
    notes, total = note_service.list_notes(user.id, skip=0, limit=limit)
    return templates.TemplateResponse(
        "components/note_card.html",
        {"request": request, "notes": notes, "total": total},
    )


@router.get("/web/notes/{note_id}", response_class=HTMLResponse)
async def note_detail(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Render note detail page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    note_service = NoteService(session)
    try:
        note = note_service.get_note(note_id, user.id)
        return templates.TemplateResponse(
            "note_detail.html",
            {"request": request, "current_user": user, "note": note},
        )
    except NotFoundError:
        return HTMLResponse(content="<div class='text-center py-8'><p>Note not found</p></div>", status_code=404)


@router.get("/web/notes/{note_id}/status", response_class=HTMLResponse)
async def note_status(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Get note processing status badge."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    note_service = NoteService(session)
    try:
        note = note_service.get_note(note_id, user.id)
        return templates.TemplateResponse(
            "components/status_badge.html",
            {"request": request, "note_id": note.id, "status": note.processing_status, "error_message": note.error_message},
        )
    except NotFoundError:
        return HTMLResponse(content="", status_code=404)


@router.get("/web/notes/{note_id}/similar", response_class=HTMLResponse)
async def similar_notes(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Get similar notes as HTML cards."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings_for_user(session, user)
    note_service = NoteService(session)

    try:
        notes = await note_service.get_similar_notes(note_id, user.id, user_settings, limit=5)
        return templates.TemplateResponse("components/similar_notes.html", {"request": request, "notes": notes})
    except (NotFoundError, Exception):
        return templates.TemplateResponse("components/similar_notes.html", {"request": request, "notes": []})


@router.get("/web/notes/{note_id}/edit/{field}", response_class=HTMLResponse)
async def edit_note_field(
    note_id: int,
    field: str,
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
):
    """Render inline edit form for a note field."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings_for_user(session, user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user.id)
        try:
            available_tags = json.loads(user_settings.custom_tags)
        except (json.JSONDecodeError, TypeError):
            available_tags = ["Idea", "Todo", "Work", "Personal", "Reference"]

        return templates.TemplateResponse(
            f"forms/edit_{field}.html",
            {"request": request, "note": note, "available_tags": available_tags},
        )
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)


# ============= Search & Ask Routes =============


@router.post("/web/search", response_class=HTMLResponse)
async def search_notes(
    request: Request,
    session: SessionDep,
    query: Annotated[str, Form()],
    access_token: Optional[str] = Cookie(default=None),
):
    """Semantic search notes and return HTML results."""
    if not query.strip():
        return HTMLResponse(content="")

    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings_for_user(session, user)
    note_service = NoteService(session)

    try:
        results = await note_service.search_notes_semantic(
            user_id=user.id, query=query, user_settings=user_settings, limit=10
        )
        return templates.TemplateResponse("components/search_results.html", {"request": request, "results": results})
    except Exception:
        return templates.TemplateResponse("components/search_results.html", {"request": request, "results": []})


@router.get("/web/ask", response_class=HTMLResponse)
async def ask_modal(request: Request):
    """Render Ask modal."""
    return templates.TemplateResponse("ask_modal.html", {"request": request})


@router.post("/web/ask", response_class=HTMLResponse)
async def ask_question(
    request: Request,
    session: SessionDep,
    question: Annotated[str, Form()],
    access_token: Optional[str] = Cookie(default=None),
):
    """Ask a question and get RAG response."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="Please log in", status_code=401)

    user_settings = get_user_settings_for_user(session, user)
    note_service = NoteService(session)

    try:
        results = await note_service.search_notes_semantic(
            user_id=user.id, query=question, user_settings=user_settings, limit=5
        )

        if not results:
            return templates.TemplateResponse(
                "components/chat_message.html",
                {
                    "request": request,
                    "question": question,
                    "answer": "I couldn't find any relevant notes to answer your question. Try recording more voice notes!",
                    "sources": [],
                },
            )

        ollama = get_ollama_service(
            base_url=user_settings.ollama_url,
            model=user_settings.ollama_model,
            api_key=user_settings.ollama_api_key,
        )
        answer = await ollama.answer_question(question, results)

        return templates.TemplateResponse(
            "components/chat_message.html",
            {"request": request, "question": question, "answer": answer, "sources": results},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "components/chat_message.html",
            {
                "request": request,
                "question": question,
                "answer": f"Sorry, I encountered an error: {str(e)}. Make sure Ollama is running.",
                "sources": [],
            },
        )


# ============= Settings Helpers =============


@router.get("/web/settings/models", response_class=HTMLResponse)
async def get_models(
    request: Request,
    session: SessionDep,
    access_token: Optional[str] = Cookie(default=None),
    ollama_url: Optional[str] = None,
):
    """Get available Ollama models as select options."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="<option>Please log in</option>")

    user_settings = get_user_settings_for_user(session, user)

    # Use provided URL or fallback to saved URL
    target_url = ollama_url if ollama_url else user_settings.ollama_url

    ollama = get_ollama_service(base_url=target_url, api_key=user_settings.ollama_api_key)

    try:
        models = await ollama.get_available_models()
        if not models:
            models = [user_settings.ollama_model]
    except Exception:
        models = [user_settings.ollama_model]

    options = []
    # Always include current model if not in list (to allow keeping it)
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
    access_token: Optional[str] = Cookie(default=None),
    ollama_url: Optional[str] = None,
):
    """Get Ollama connection status."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="<p>Please log in</p>")

    user_settings = get_user_settings_for_user(session, user)
    
    # Use provided URL or fallback to saved URL
    target_url = ollama_url if ollama_url else user_settings.ollama_url
    
    ollama = get_ollama_service(base_url=target_url, api_key=user_settings.ollama_api_key)
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
    access_token: Optional[str] = Cookie(default=None),
    ollama_url: Annotated[str | None, Form()] = None,
    ollama_model: Annotated[str | None, Form()] = None,
    ollama_api_key: Annotated[str | None, Form()] = None,
    custom_tags: Annotated[str | None, Form()] = None,
):
    """
    Update user settings (HTMX Form).
    
    Accepts form data, processes tags, and updates the database.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings_for_user(session, user)

    if ollama_url is not None:
        user_settings.ollama_url = ollama_url
    
    if ollama_model is not None:
        user_settings.ollama_model = ollama_model
        
    if ollama_api_key is not None:
        # Handle empty string as None/empty
        user_settings.ollama_api_key = ollama_api_key if ollama_api_key.strip() else None

    if custom_tags is not None:
        # Split by comma and strip whitespace
        tags_list = [tag.strip() for tag in custom_tags.split(",") if tag.strip()]
        user_settings.custom_tags = json.dumps(tags_list)

    session.add(user_settings)
    session.commit()
    
    return HTMLResponse(content="", status_code=200)
