"""Pydantic schemas for request/response validation."""

from app.schemas.auth import Token, TokenData, UserCreate, UserResponse
from app.schemas.note import (
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
    SimilarNotesResponse,
)
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.settings import (
    ModelsResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)

__all__ = [
    "Token",
    "TokenData",
    "UserCreate",
    "UserResponse",
    "NoteListResponse",
    "NoteResponse",
    "NoteUpdate",
    "SimilarNotesResponse",
    "SearchRequest",
    "SearchResponse",
    "ModelsResponse",
    "UserSettingsResponse",
    "UserSettingsUpdate",
]
