"""Notes CRUD endpoints."""

import uuid
from pathlib import Path
from typing import Annotated, Union, cast

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)

from app.api.deps import CurrentUserDep, SessionDep, UserSettingsDep
from app.schemas.note import (
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
    SimilarNotesResponse,
)
from app.services.note_service import NoteService
from app.tasks.processing_tasks import process_new_note, reprocess_note
from app.utils.events import event_manager
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/api", tags=["notes"])

# Directory for storing uploaded audio files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post(
    "/upload", response_model=NoteResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_voice_note(
    audio_file: Annotated[UploadFile, File(description="Audio file to transcribe")],
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> NoteResponse:
    """
    Upload a voice note for transcription and processing.

    The note is created immediately with 'pending' status, and processing
    happens in the background. Poll the note endpoint to check status.
    """
    assert current_user.id is not None
    print("\n[DEBUG] Reached upload_voice_note handler")
    print(f"[DEBUG] audio_file filename: {audio_file.filename}")
    print(f"[DEBUG] audio_file content_type: {audio_file.content_type}")
    # Read file content
    content = await audio_file.read()

    # Generate unique filename
    file_extension = Path(audio_file.filename or "audio.m4a").suffix or ".m4a"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Create note with pending status
    note_service = NoteService(session)
    note = note_service.create_note(
        user_id=current_user.id,
        audio_path=str(file_path),
    )

    # Trigger background processing
    assert note.id is not None
    background_tasks.add_task(process_new_note, note.id)

    # Broadcast event
    await event_manager.broadcast(
        cast(int, current_user.id), "note-created", str(note.id)
    )

    return NoteResponse.model_validate(note)


@router.get("/notes", response_model=NoteListResponse)
def list_notes(
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> NoteListResponse:
    """
    List all notes for the current user with pagination.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    notes, total = note_service.list_notes(current_user.id, skip=skip, limit=limit)
    return NoteListResponse(
        notes=[NoteResponse.model_validate(n) for n in notes],
        total=total,
    )


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NoteResponse:
    """
    Get a single note by ID.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note = note_service.get_note(note_id, current_user.id)
        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    update_data: NoteUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> NoteResponse:
    """
    Update a note's content or tag.

    If the transcript is changed, the note will be reprocessed
    to generate new summary, tag, and embedding.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note = note_service.update_note(
            note_id,
            current_user.id,
            raw_transcript=update_data.raw_transcript,
            tag=update_data.tag,
        )

        # If transcript was updated, trigger reprocessing
        if update_data.raw_transcript is not None:
            background_tasks.add_task(reprocess_note, cast(int, note.id))

        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.post("/notes/{note_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_failed_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Retry processing a failed note.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note = note_service.get_note(note_id, current_user.id)

        if note.processing_status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed notes can be retried",
            )

        # Update status to processing immediately
        note.processing_status = "processing"
        note.error_message = None
        session.add(note)
        session.commit()

        # Trigger background reprocessing
        background_tasks.add_task(reprocess_note, cast(int, note.id))

        # Broadcast status update for SSE
        await event_manager.broadcast(
            cast(int, current_user.id), f"note-status-{note.id}", "processing"
        )

        return {"message": "Note reprocessing started"}
    except NotFoundError as e:
        raise e.to_http_exception()


@router.patch("/notes/{note_id}/archive", response_model=NoteResponse)
async def archive_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NoteResponse:
    """
    Archive a note (soft delete - hide from recent/search).
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note = note_service.archive_note(note_id, current_user.id)
        await event_manager.broadcast(current_user.id, "note-archived", str(note_id))
        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.patch("/notes/{note_id}/unarchive", response_model=NoteResponse)
async def unarchive_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NoteResponse:
    """
    Unarchive a note (restore from soft delete).
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note = note_service.unarchive_note(note_id, current_user.id)
        await event_manager.broadcast(current_user.id, "note-unarchived", str(note_id))
        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.delete("/notes/{note_id}", response_model=None)
async def delete_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
    request: Request,
) -> Union[dict, Response]:
    """
    Delete a note.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        note_service.delete_note(note_id, current_user.id)
        await event_manager.broadcast(current_user.id, "note-deleted", str(note_id))

        # Return JSON for API calls, HTML redirect for HTMX
        if request.headers.get("hx-request"):
            return Response(headers={"HX-Redirect": "/"})
        else:
            return {"success": True}
    except NotFoundError as e:
        raise e.to_http_exception()


@router.get("/notes/{note_id}/similar", response_model=SimilarNotesResponse)
async def get_similar_notes(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    user_settings: UserSettingsDep,
) -> SimilarNotesResponse:
    """
    Get notes similar to the specified note.

    Uses vector similarity to find related notes.
    """
    assert current_user.id is not None
    note_service = NoteService(session)
    try:
        similar = await note_service.get_similar_notes(
            note_id, cast(int, current_user.id), user_settings, limit=5
        )
        return SimilarNotesResponse(
            similar=[NoteResponse.model_validate(n) for n in similar]
        )
    except NotFoundError as e:
        raise e.to_http_exception()
