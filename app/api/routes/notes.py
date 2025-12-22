"""Notes CRUD endpoints."""

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUserDep, SessionDep, UserSettingsDep
from app.schemas.note import NoteListResponse, NoteResponse, NoteUpdate, SimilarNotesResponse
from app.services.note_service import NoteService
from app.tasks.processing_tasks import process_new_note, reprocess_note
from app.utils.exceptions import NotFoundError

router = APIRouter(prefix="/api", tags=["notes"])

# Directory for storing uploaded audio files
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=NoteResponse, status_code=status.HTTP_202_ACCEPTED)
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
    print(f"\n[DEBUG] Reached upload_voice_note handler")
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
    background_tasks.add_task(process_new_note, note.id)

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
    note_service = NoteService(session)
    try:
        note = note_service.get_note(note_id, current_user.id)
        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(
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
            background_tasks.add_task(reprocess_note, note.id)

        return NoteResponse.model_validate(note)
    except NotFoundError as e:
        raise e.to_http_exception()


@router.delete("/notes/{note_id}", status_code=status.HTTP_200_OK)
def delete_note(
    note_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict:
    """
    Delete a note.
    """
    note_service = NoteService(session)
    try:
        note_service.delete_note(note_id, current_user.id)
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
    note_service = NoteService(session)
    try:
        similar = await note_service.get_similar_notes(
            note_id, current_user.id, user_settings, limit=5
        )
        return SimilarNotesResponse(
            similar=[NoteResponse.model_validate(n) for n in similar]
        )
    except NotFoundError as e:
        raise e.to_http_exception()
