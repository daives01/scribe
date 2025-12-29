"""Search web routes for HTMX frontend."""

from typing import Annotated, cast

from fastapi import Cookie, Form, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, get_user_settings
from app.services.note_service import NoteService

from . import get_current_user_from_cookie, logger, router, templates


@router.post("/web/search", response_class=HTMLResponse)
async def search_notes(
    request: Request,
    session: SessionDep,
    q: Annotated[str | None, Form()] = "",
    access_token: str | None = Cookie(default=None),
):
    """Semantic search notes and return HTML results."""
    if not q or not q.strip():
        return HTMLResponse(content="")

    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_settings = get_user_settings(session, user)
    note_service = NoteService(session)

    try:
        results = await note_service.search_notes_semantic(
            user_id=cast(int, user.id), query=q, user_settings=user_settings, limit=5
        )
        return templates.TemplateResponse(
            "components/search_results.html",
            {"request": request, "results": [(r, None) for r in results]},
        )
    except Exception as e:
        logger.exception(f"Error in search_notes: {e}")
        return templates.TemplateResponse(
            "components/search_results.html",
            {"request": request, "results": [], "error": str(e)},
        )

