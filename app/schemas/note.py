"""Note schemas."""

from datetime import datetime

from pydantic import BaseModel


class NoteCreate(BaseModel):
    """Schema for note creation (internal use)."""

    raw_transcript: str = ""
    audio_path: str | None = None


class NoteUpdate(BaseModel):
    """Schema for note updates."""

    raw_transcript: str | None = None
    tag: str | None = None


class NoteResponse(BaseModel):
    """Schema for note response."""

    id: int
    raw_transcript: str
    summary: str | None
    tag: str | None
    notification_timestamp: datetime | None
    processing_status: str
    error_message: str | None
    archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """Schema for paginated note list."""

    notes: list[NoteResponse]
    total: int


class SimilarNotesResponse(BaseModel):
    """Schema for similar notes response."""

    similar: list[NoteResponse]
