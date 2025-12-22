"""User and UserSettings models."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


if TYPE_CHECKING:
    from app.models.note import Note


class User(SQLModel, table=True):
    """User account model."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_utc_now)

    # Long-lived API token for mobile/Siri shortcuts
    api_token: str | None = Field(default=None, unique=True, index=True)

    # Relationships
    settings: "UserSettings" = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"},
    )
    notes: list["Note"] = Relationship(back_populates="user")


class UserSettings(SQLModel, table=True):
    """Per-user settings for AI configuration."""

    __tablename__ = "user_settings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)

    # AI Configuration
    ollama_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen3:4b-instruct")
    ollama_embedding_model: str = Field(default="nomic-embed-text")
    ollama_api_key: str | None = Field(default=None)

    # User-defined tags (JSON array stored as string)
    custom_tags: str = Field(
        default='["Idea", "Todo", "Work", "Personal", "Reference"]'
    )

    # Relationships
    user: User = Relationship(back_populates="settings")
