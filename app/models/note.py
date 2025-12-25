"""Note model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Index, LargeBinary
from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime import utc_now

if TYPE_CHECKING:
    from app.models.user import User


class Note(SQLModel, table=True):  # type: ignore
    """Voice note model with transcript and AI-generated metadata."""

    __tablename__ = "notes"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    # Content
    raw_transcript: str = Field(default="")
    summary: str | None = Field(default=None)  # <5 word summary
    tag: str | None = Field(default=None)
    notification_timestamp: datetime | None = Field(
        default=None, index=True
    )  # When to send notification

    # Audio storage path (for re-processing if needed)
    audio_path: str | None = Field(default=None)

    # Vector embedding (stored as BLOB - serialized numpy array)
    embedding: bytes | None = Field(default=None, sa_column=Column(LargeBinary))

    # Processing state
    processing_status: str = Field(
        default="pending", index=True
    )  # pending, transcribing, processing, completed, failed
    error_message: str | None = Field(default=None)

    # Archive state
    archived: bool = Field(default=False, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    user: "User" = Relationship(back_populates="notes")

    __table_args__ = (
        Index("ix_notes_user_status", "user_id", "processing_status"),
        Index("ix_notes_user_created", "user_id", "created_at"),
        Index("ix_notes_user_archived_created", "user_id", "archived", "created_at"),
    )
