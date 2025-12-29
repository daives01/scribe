"""Note web routes for HTMX frontend."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import BackgroundTasks, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import SessionDep, get_user_settings
from app.services.note_service import NoteService
from app.tasks.processing_tasks import process_new_note
from app.utils import get_custom_tags
from app.utils.events import event_manager
from app.utils.exceptions import NotFoundError

from . import (
    get_current_user_from_cookie,
    logger,
    require_user_id,
    router,
    templates,
)


def _parse_table_filters(
    archive_filter: str,
    date_from: str | None,
    date_to: str | None,
) -> tuple[tuple[bool, bool], datetime | None, datetime | None]:
    """Parse table filter parameters."""
    if archive_filter == "active":
        include_archived = False
        archived_only = False
    elif archive_filter == "all":
        include_archived = True
        archived_only = False
    elif archive_filter == "archived":
        include_archived = False
        archived_only = True
    else:
        include_archived = False
        archived_only = False

    parsed_date_from = None
    parsed_date_to = None

    if date_from:
        try:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d").replace(
                tzinfo=UTC
            )
        except ValueError:
            pass

    if date_to:
        try:
            parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=UTC
            )
        except ValueError:
            pass

    return (include_archived, archived_only), parsed_date_from, parsed_date_to


@router.get("/web/notes/{note_id}/similar", response_class=HTMLResponse)
async def get_similar_notes_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Get similar notes for a note."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)
    user_id = require_user_id(user)

    user_settings = get_user_settings(session, user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user_id)
        if note.processing_status != "completed":
            return templates.TemplateResponse(
                "components/similar_notes.html",
                {"request": request, "notes": [], "processing": True},
            )

        notes = await note_service.get_similar_notes(
            note_id, user_id, user_settings, limit=5
        )
        return templates.TemplateResponse(
            "components/similar_notes.html", {"request": request, "notes": notes}
        )
    except NotFoundError:
        return HTMLResponse(content="", status_code=404)
    except Exception as e:
        logger.exception(f"Error in similar_notes: {e}")
        return templates.TemplateResponse(
            "components/similar_notes.html",
            {"request": request, "notes": [], "error": str(e)},
        )


@router.get("/web/notes/{note_id}/edit/{field}", response_class=HTMLResponse)
async def edit_note_field(
    note_id: int,
    field: str,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Render inline edit form for a note field."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    user_settings = get_user_settings(session, user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user_id)
        available_tags = get_custom_tags(user_settings.custom_tags)

        return templates.TemplateResponse(
            f"forms/edit_{field}.html",
            {"request": request, "note": note, "available_tags": available_tags},
        )
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)


@router.patch("/web/notes/{note_id}", response_class=HTMLResponse)
async def update_note_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    raw_transcript: Annotated[str | None, Form()] = None,
    summary: Annotated[str | None, Form()] = None,
    tag: Annotated[str | None, Form()] = None,
):
    """
    Update a note via web form (HTMX).

    Returns the updated note card HTML for real-time updates.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        note_service.update_note(
            note_id,
            user_id,
            raw_transcript=raw_transcript,
            summary=summary,
            tag=tag,
        )

        note = note_service.get_note(note_id, user_id)
        return templates.TemplateResponse(
            "components/note_card.html",
            {
                "request": request,
                "notes": [note],
                "total": 1,
                "show_count": False,
            },
        )
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)
    except Exception as e:
        logger.exception(f"Error updating note: {e}")
        return HTMLResponse(content="Error updating note", status_code=500)


@router.get("/web/notes/table", response_class=HTMLResponse)
async def get_notes_table_page(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Render all notes table page."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_settings = get_user_settings(session, user)
    custom_tags = get_custom_tags(user_settings.custom_tags)

    return templates.TemplateResponse(
        "notes_table.html",
        {
            "request": request,
            "current_user": user,
            "available_tags": custom_tags,
        },
    )


@router.get("/web/notes/table/data", response_class=HTMLResponse)
async def get_notes_table_data(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    search: str | None = None,
    tag: str | None = None,
    status: str | None = None,
    archive_filter: str = "active",
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20,
):
    """
    Get notes table body (HTMX partial).

    Supports filtering, sorting, and pagination.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    (include_archived, archived_only), parsed_date_from, parsed_date_to = (
        _parse_table_filters(archive_filter, date_from, date_to)
    )

    try:
        notes, total = note_service.list_notes_advanced(
            user_id=user_id,
            search=search,
            tag=tag if tag and tag != "all" else None,
            status=status if status and status != "all" else None,
            include_archived=include_archived,
            archived_only=archived_only,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

        start = (page - 1) * per_page + 1
        end = min(start + per_page - 1, total)

        return templates.TemplateResponse(
            "components/notes_table_body.html",
            {
                "request": request,
                "notes": notes,
                "total": total,
                "page": page,
                "per_page": per_page,
                "start": start if notes else 0,
                "end": end if notes else 0,
                "search": search or "",
                "tag": tag or "all",
                "status": status or "all",
                "archive_filter": archive_filter,
                "date_from": date_from or "",
                "date_to": date_to or "",
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
    except Exception as e:
        logger.exception(f"Error loading notes table data: {e}")
        return HTMLResponse(content="", status_code=500)


@router.get("/web/notes/table/components/pagination", response_class=HTMLResponse)
async def get_notes_table_pagination(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    page: int = 1,
    per_page: int = 20,
    search: str = "",
    tag: str = "all",
    status: str = "all",
    archive_filter: str = "active",
    date_from: str = "",
    date_to: str = "",
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    """Render pagination component for notes table."""
    user = await get_current_user_from_cookie(
        request, session=session, access_token=access_token
    )
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    (include_archived, archived_only), parsed_date_from, parsed_date_to = (
        _parse_table_filters(archive_filter, date_from, date_to)
    )

    try:
        _, computed_total = note_service.list_notes_advanced(
            user_id=user_id,
            search=search if search else None,
            tag=tag if tag and tag != "all" else None,
            status=status if status and status != "all" else None,
            include_archived=include_archived,
            archived_only=archived_only,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page,
        )

        start = (page - 1) * per_page + 1
        end = min(start + per_page - 1, computed_total)

        return templates.TemplateResponse(
            "components/pagination.html",
            {
                "request": request,
                "total": computed_total,
                "page": page,
                "per_page": per_page,
                "start": start if computed_total > 0 else 0,
                "end": end if computed_total > 0 else 0,
                "search": search,
                "tag": tag,
                "status": status,
                "archive_filter": archive_filter,
                "date_from": date_from,
                "date_to": date_to,
                "sort_by": sort_by,
                "sort_order": sort_order,
            },
        )
    except Exception as e:
        logger.exception(f"Error loading pagination: {e}")
        return HTMLResponse(content="", status_code=500)


@router.post("/web/notes/table/bulk", response_class=HTMLResponse)
async def bulk_notes_action(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
    note_ids: Annotated[str | None, Form()] = None,
    action: Annotated[str | None, Form()] = None,
):
    """
    Handle bulk actions on notes (archive, unarchive, delete).

    Returns updated table body.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    if not note_ids or not action:
        return HTMLResponse(content="", status_code=400)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        parsed_ids = [
            int(id_str.strip())
            for id_str in note_ids.split(",")
            if id_str.strip() and id_str.strip().isdigit()
        ]
        if not parsed_ids:
            return HTMLResponse(content="", status_code=400)
    except (ValueError, AttributeError):
        return HTMLResponse(content="", status_code=400)

    try:
        if action == "archive":
            note_service.bulk_archive_notes(parsed_ids, user_id)
            for note_id in parsed_ids:
                await event_manager.broadcast(user_id, "note-archived", str(note_id))
        elif action == "unarchive":
            note_service.bulk_unarchive_notes(parsed_ids, user_id)
            for note_id in parsed_ids:
                await event_manager.broadcast(user_id, "note-unarchived", str(note_id))
        elif action == "delete":
            deleted_ids = note_service.bulk_delete_notes(parsed_ids, user_id)
            for note_id in deleted_ids:
                await event_manager.broadcast(user_id, "note-deleted", str(note_id))

        return HTMLResponse(content="", status_code=200)
    except Exception as e:
        logger.exception(f"Error in bulk action: {e}")
        return HTMLResponse(content="Error performing bulk action", status_code=500)


@router.patch("/web/notes/{note_id}/archive", response_class=HTMLResponse)
async def archive_note_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Archive a note (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)
    user_id = require_user_id(user)

    note_service = NoteService(session)
    try:
        note_service.archive_note(note_id, user_id)
        return HTMLResponse(content="", status_code=200)
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)


@router.patch("/web/notes/{note_id}/unarchive", response_class=HTMLResponse)
async def unarchive_note_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Unarchive a note (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)
    user_id = require_user_id(user)

    note_service = NoteService(session)
    try:
        note_service.unarchive_note(note_id, user_id)
        return HTMLResponse(content="", status_code=200)
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)


@router.delete("/web/notes/{note_id}", response_class=HTMLResponse)
async def delete_note_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
):
    """Delete a note (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)
    user_id = require_user_id(user)

    note_service = NoteService(session)
    try:
        note_service.delete_note(note_id, user_id)
        await event_manager.broadcast(user_id, "note-deleted", str(note_id))
        return HTMLResponse(content="", status_code=200)
    except NotFoundError:
        return HTMLResponse(content="Note not found", status_code=404)


@router.post("/web/notes/text", response_class=HTMLResponse)
async def create_text_note_web(
    request: Request,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    text: Annotated[str, Form()] = "",
    access_token: str | None = Cookie(default=None),
):
    """Create a new text note (HTMX)."""
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        note = note_service.create_note(
            user_id=user_id,
            raw_transcript=text,
            audio_path=None,
        )

        if note.id is None:
            return HTMLResponse(content="Failed to create note", status_code=500)
        background_tasks.add_task(process_new_note, note.id)

        await event_manager.broadcast(user_id, "note-created", str(note.id))

        return templates.TemplateResponse(
            "components/note_card.html",
            {
                "request": request,
                "notes": [note],
                "total": 1,
                "show_count": False,
            },
        )
    except Exception as e:
        logger.exception(f"Error creating text note: {e}")
        return HTMLResponse(content="", status_code=500)


@router.get("/web/notes/recent", response_class=HTMLResponse)
async def get_recent_notes_web(
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Get recent notes for the home page (HTMX).

    Returns HTML for note cards, excluding archived notes.
    Used for initial page load and real-time updates via SSE.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        notes, total = note_service.list_notes(user_id, skip=0, limit=100)

        return templates.TemplateResponse(
            "components/note_card.html",
            {
                "request": request,
                "notes": notes,
                "total": total,
                "show_count": True,
            },
        )
    except Exception as e:
        logger.exception(f"Error loading recent notes: {e}")
        return templates.TemplateResponse(
            "components/note_card.html",
            {
                "request": request,
                "notes": [],
                "total": 0,
                "show_count": True,
            },
        )


@router.get("/web/notes/{note_id}/card", response_class=HTMLResponse)
async def get_note_card_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Get note card HTML for SSE updates (HTMX).

    Returns HTML for a single note card, used for live updates.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user_id)
        return templates.TemplateResponse(
            "components/note_card.html",
            {
                "request": request,
                "notes": [note],
                "total": 1,
                "show_count": False,
            },
        )
    except NotFoundError:
        return HTMLResponse(content="", status_code=404)
    except Exception as e:
        logger.exception(f"Error loading note card: {e}")
        return HTMLResponse(content="", status_code=500)


@router.get("/web/notes/{note_id}/modal", response_class=HTMLResponse)
async def get_note_modal_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Get note modal HTML (HTMX).

    Returns HTML for note modal, used for inline editing.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user_id)
        user_settings = get_user_settings(session, user)
        available_tags = get_custom_tags(user_settings.custom_tags)

        return templates.TemplateResponse(
            "components/note_modal.html",
            {
                "request": request,
                "note": note,
                "available_tags": available_tags,
                "now": datetime.now(UTC),
            },
        )
    except NotFoundError:
        return HTMLResponse(content="", status_code=404)
    except Exception as e:
        logger.exception(f"Error loading note modal: {e}")
        return HTMLResponse(content="", status_code=500)


@router.get("/web/notes/{note_id}/status", response_class=HTMLResponse)
async def get_note_status_web(
    note_id: int,
    request: Request,
    session: SessionDep,
    access_token: str | None = Cookie(default=None),
) -> HTMLResponse:
    """
    Get note status badge HTML for SSE updates (HTMX).

    Returns HTML for the status badge, used for live updates.
    """
    user = await get_current_user_from_cookie(request, session, access_token)
    if not user:
        return HTMLResponse(content="", status_code=401)

    user_id = require_user_id(user)
    note_service = NoteService(session)

    try:
        note = note_service.get_note(note_id, user_id)
        return templates.TemplateResponse(
            "components/status_badge.html",
            {
                "request": request,
                "note": note,
                "note_id": note_id,
            },
        )
    except NotFoundError:
        return HTMLResponse(content="", status_code=404)
    except Exception as e:
        logger.exception(f"Error loading note status: {e}")
        return HTMLResponse(content="", status_code=500)

